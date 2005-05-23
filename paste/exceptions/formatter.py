"""
Formatters for the exception data that comes from ExceptionCollector.
"""

import cgi

def html_quote(s):
    return cgi.escape(s, True)

class AbstractFormatter:

    general_data_order = ['object', 'source_url']

    def __init__(self, show_hidden_frames=False,
                 include_reusable=True,
                 trim_source_paths=()):
        self.show_hidden_frames = show_hidden_frames
        self.trim_source_paths = trim_source_paths
        self.include_reusable = include_reusable

    def format_collected_data(self, exc_data):
        general_data = {}
        for name, value_list in exc_data.extra_data.items():
            if isinstance(name, tuple):
                importance, title = name
            else:
                importance, title = 'normal', name
            for value in value_list:
                general_data[(importance, name)] = self.format_extra_data(
                    importance, title, value)
        lines = []
        frames = self.filter_frames(exc_data.frames)
        for frame in frames:
            sup = frame.supplement
            if sup:
                if sup.object:
                    general_data[('important', 'object')] = self.format_sup_object(
                        sup.object)
                if sup.source_url:
                    general_data[('important', 'source_url')] = self.format_sup_url(
                        sup.source_url)
                if sup.line:
                    lines.append(self.format_sup_line_pos(sup.line, sup.column))
                if sup.expression:
                    lines.append(self.format_sup_expression(sup.expression))
                if sup.warnings:
                    for warning in sup.warnings:
                        lines.append(self.format_sup_warning(warning))
                if sup.info:
                    lines.extend(self.format_sup_info(sup.info))
            if frame.supplement_exception:
                lines.append('Exception in supplement:')
                lines.append(self.quote_long(frame.supplement_exception))
            if frame.traceback_info:
                lines.append(self.format_traceback_info(frame.traceback_info))
            filename = frame.filename
            if filename and self.trim_source_paths:
                for path, repl in self.trim_source_paths:
                    if filename.startswith(path):
                        filename = repl + filename[len(path):]
                        break
            lines.append(self.format_source_line(
                filename or '?',
                frame.lineno or '?',
                frame.name or '?'))
            source = frame.get_source_line()
            if source:
                lines.append(self.format_source(source))
        exc_info = self.format_exception_info(
            exc_data.exception_type,
            exc_data.exception_value)
        data_by_importance = {'important': [], 'normal': [],
                              'supplemental': [], 'extra': []}
        for (importance, name), value in general_data.items():
            data_by_importance[importance].append(
                (name, value))
        for value in data_by_importance.values():
            value.sort()
        return self.format_combine(data_by_importance, lines, exc_info)

    def filter_frames(self, frames):
        """
        Removes any frames that should be hidden, according to the
        values of traceback_hide, self.show_hidden_frames, and the
        hidden status of the final frame.
        """
        if self.show_hidden_frames:
            return frames
        new_frames = []
        hidden = False
        for frame in frames:
            hide = frame.traceback_hide
            # @@: It would be nice to signal a warning if an unknown
            # hide string was used, but I'm not sure where to put
            # that warning.
            if hide == 'before':
                new_frames = []
                hidden = False
            elif hide == 'before_and_this':
                new_frames = []
                hidden = False
                continue
            elif hide == 'reset':
                hidden = False
            elif hide == 'reset_and_this':
                hidden = False
                continue
            elif hide == 'after':
                hidden = True
            elif hide == 'after_and_this':
                hidden = True
                continue
            elif hide:
                continue
            elif hidden:
                continue
            new_frames.append(frame)
        if frames[-1] not in new_frames:
            # We must include the last frame; that we don't indicates
            # that the error happened where something was "hidden",
            # so we just have to show everything
            return frames
        return new_frames

    def pretty_string_repr(self, s):
        """
        Formats the string as a triple-quoted string when it contains
        newlines.
        """
        if '\n' in s:
            s = repr(s)
            s = s[0]*3 + s[1:-1] + s[-1]*3
            s = s.replace('\\n', '\n')
            return s
        else:
            return repr(s)

    def long_item_list(self, lst):
        """
        Returns true if the list contains items that are long, and should
        be more nicely formatted.
        """
        how_many = 0
        for item in lst:
            if len(repr(item)) > 40:
                how_many += 1
                if how_many >= 3:
                    return True
        return False

class TextFormatter(AbstractFormatter):

    def quote(self, s):
        return s
    def quote_long(self, s):
        return s
    def emphasize(self, s):
        return s
    def format_sup_object(self, obj):
        return 'In object: %s' % self.quote(repr(obj))
    def format_sup_url(self, url):
        return 'URL: %s' % self.quote(url)
    def format_sup_line_pos(self, line, column):
        if column:
            return 'Line %i, Column %i' % (line, column)
        else:
            return 'Line %i' % line
    def format_sup_expression(self, expr):
        return 'In expression: %s' % self.quote(expr)
    def format_sup_warning(self, warning):
        return 'Warning: %s' % self.quote(warning)
    def format_sup_info(self, info):
        return [self.quote(info)]
    def format_source_line(self, filename, lineno, name):
        return 'File %r, line %s in %s' % (filename, lineno, name)
    def format_source(self, source_line):
        return '  ' + self.quote(source_line.strip())
    def format_exception_info(self, etype, evalue):
        return self.emphasize(
            '%s: %s' % (self.quote(etype), self.quote(evalue)))
    def format_traceback_info(self, info):
        return info
        
    def format_combine(self, data_by_importance, lines, exc_info):
        lines[:0] = [value for n, value in data_by_importance['important']]
        lines.append(exc_info)
        for name in 'normal', 'supplemental', 'extra':
            lines.extend([value for n, value in data_by_importance[name]])
        return self.format_combine_lines(lines)

    def format_combine_lines(self, lines):
        return '\n'.join(lines)

    def format_extra_data(self, importance, title, value):
        if isinstance(value, str):
            s = self.pretty_string_repr(value)
            if '\n' in s:
                return '%s:\n%s' % (title, s)
            else:
                return '%s: %s' % (title, s)
        elif isinstance(value, dict):
            lines = [title, '-'*len(title)]
            items = value.items()
            items.sort()
            for n, v in items:
                lines.append('%s: %s' % (n, repr(v)))
            return '\n'.join(lines)
        elif (isinstance(value, (list, tuple))
              and self.long_item_list(value)):
            return '%s: [,\n    %s]' % (
                title, '\n    '.join(map(repr, value)))
        else:
            return '%s: %r' % (title, value)

class HTMLFormatter(TextFormatter):

    def quote(self, s):
        return html_quote(s)
    def quote_long(self, s):
        return '<pre>%s</pre>' % self.quote(s)
    def emphasize(self, s):
        return '<b>%s</b>' % s
    def format_sup_url(self, url):
        return 'URL: <a href="%s">%s</a>' % (url, url)
    def format_combine_lines(self, lines):
        return '<br>\n'.join(lines)
    def format_source_line(self, filename, lineno, name):
        return 'File %r, line %s in <tt>%s</tt>' % (filename, lineno, name)
    def format_source(self, source_line):
        return '&nbsp;&nbsp;<tt>%s</tt>' % self.quote(source_line.strip())
    def format_traceback_info(self, info):
        return '<pre>%s</pre>' % self.quote(info)

    def format_extra_data(self, importance, title, value):
        if isinstance(value, str):
            s = self.pretty_string_repr(value)
            if '\n' in s:
                return '%s:<br><pre>%s</pre>' % (title, self.quote(s))
            else:
                return '%s: <tt>%s</tt>' % (title, self.quote(s))
        elif isinstance(value, dict):
            return self.zebra_table(title, value)
        elif (isinstance(value, (list, tuple))
              and self.long_item_list(value)):
            return '%s: <tt>[<br>\n&nbsp; &nbsp; %s]</tt>' % (
                title, ',<br>&nbsp; &nbsp; '.join(map(self.quote, map(repr, value))))
        else:
            return '%s: <tt>%s</tt>' % (title, self.quote(repr(value)))

    def format_combine(self, data_by_importance, lines, exc_info):
        lines[:0] = [value for n, value in data_by_importance['important']]
        lines.append(exc_info)
        for name in 'normal', 'supplemental':
            lines.extend([value for n, value in data_by_importance[name]])
        if data_by_importance['extra']:
            lines.append(
                '<script type="text/javascript">\nshow_button(\'extra_data\', \'extra data\');\n</script>\n' +
                '<div id="extra_data" class="hidden-data">\n')
            lines.extend([value for n, value in data_by_importance['extra']])
            lines.append('</div>')
        text = self.format_combine_lines(lines)
        if self.include_reusable:
            return error_css + hide_display_js + text
        else:
            # Usually because another error is already on this page,
            # and so the js & CSS are unneeded
            return text

    def zebra_table(self, title, rows, table_class="variables"):
        if isinstance(rows, dict):
            rows = rows.items()
            rows.sort()
        table = ['<table class="%s">' % table_class,
                 '<tr class="header"><th colspan="2">%s</th></tr>'
                 % self.quote(title)]
        odd = False
        for name, value in rows:
            odd = not odd
            table.append(
                '<tr class="%s"><td>%s</td>'
                % (odd and 'odd' or 'even', self.quote(name)))
            table.append(
                '<td><tt>%s</tt></td></tr>'
                % self.make_wrappable(self.quote(repr(value))))
        table.append('</table>')
        return '\n'.join(table)

    def make_wrappable(self, html, wrap_limit=60,
                       split_on=';?&@!$#-/\\"\''):
        # Currently using <wbr>, maybe should use &#8203;
        #   http://www.cs.tut.fi/~jkorpela/html/nobr.html
        words = html.split()
        new_words = []
        for word in words:
            if len(word) > wrap_limit:
                for char in split_on:
                    if char in word:
                        words = [
                            self.make_wrappable(w, wrap_limit=wrap_limit,
                                                split_on=split_on)
                            for w in word.split(char, 1)]
                        new_words.append('<wbr>'.join(words))
                        break
            else:
                new_words.append(word)
        return ' '.join(new_words)

hide_display_js = r'''
<script type="text/javascript">
function hide_display(id) {
  var el = document.getElementById(id);
  if (el.className == "hidden-data") {
    el.className = "";
    return true;
  } else {
    el.className = "hidden-data";
    return false;
  }
}
document.write('<style type="text/css">\n');
document.write('.hidden-data {display: none}\n');
document.write('</style>\n');
function show_button(toggle_id, name) {
  document.write('<a href="#' + toggle_id
      + '" onclick="javascript:hide_display(\'' + toggle_id
      + '\')" class="button">' + name + '</a><br>');
}
</script>'''
    

error_css = """
<style type="text/css">
table {
  width: 100%;
}

tr.header {
  background-color: #006;
  color: #fff;
}

tr.even {
  background-color: #ddd;
}

table.variables td {
  verticle-align: top;
  overflow: auto;
}

a.button {
  background-color: #ccc;
  border: 2px outset #aaa;
  color: #000;
  text-decoration: none;
}

a.button:hover {
  background-color: #ddd;
}
</style>
"""

def format_html(exc_data, include_hidden_frames=False, **ops):
    if not include_hidden_frames:
        return HTMLFormatter(**ops).format_collected_data(exc_data)
    short_er = format_html(exc_data, show_hidden_frames=False, **ops)
    # @@: This should have a way of seeing if the previous traceback
    # was actually trimmed at all
    long_er = format_html(exc_data, show_hidden_frames=True,
                          include_reusable=False, **ops)
    return """
    %s
    <br>
    <script type="text/javascript">
    show_button('full_traceback', 'full traceback')
    </script>
    <div id="full_traceback" class="hidden-data">
    %s
    </div>
    """ % (short_er, long_er)
        
def format_text(exc_data, **ops):
    return TextFormatter(**ops).format_collected_data(exc_data)

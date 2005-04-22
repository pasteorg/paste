"""
Formatters for the exception data that comes from ExceptionCollector.
"""

import cgi
import serial_number_generator

def html_quote(s):
    return cgi.escape(s, True)

class AbstractFormatter:

    general_data_order = ['object', 'source_url']

    def __init__(self, show_hidden_frames=False,
                 trim_source_paths=()):
        self.show_hidden_frames = show_hidden_frames
        self.trim_source_paths = trim_source_paths

    def format_collected_data(self, exc_data):
        general_data = {}
        lines = []
        show_hidden_frames = self.show_hidden_frames
        last = exc_data.frames[-1]
        if last.traceback_hide or last.traceback_stop:
            # If the last frame was supposed to have been hidden,
            # there's clearly a problem in the hidden portion of
            # the framework itself
            show_hidden_frames = True
        for frame in exc_data.frames:
            if frame.traceback_hide and not show_hidden_frames:
                continue
            sup = frame.supplement
            if sup:
                if sup.object:
                    general_data['object'] = self.format_sup_object(
                        sup.object)
                if sup.source_url:
                    general_data['source_url'] = self.format_sup_url(
                        sup.source_url)
                if sup.line:
                    lines.append(self.format_sup_line_pos(self.line, self.column))
                if sup.expression:
                    lines.append(self.format_sup_expression(sup.expression))
                if sup.warnings:
                    for warning in sup.warnings:
                        lines.append(self.format_sup_warning(warning))
                if sup.info:
                    lines.extend(self.format_sup_info(sup.info))
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
        general_data = general_data.items()
        general_data.sort(
            lambda a, b, self=self:
            cmp(self.general_data_order.index(a[0]),
                self.general_data_order.index(b[0])))
        return self.format_combine(general_data, lines, exc_info)

class TextFormatter(AbstractFormatter):

    def quote(self, s):
        return s
    def emphasize(self, s):
        return s
    def format_sup_object(self, name):
        return 'In object: %s' % self.quote(name)
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
    def format_combine(self, general_data, lines, exc_info):
        lines[:0] = [value for name, value in general_data]
        lines.append(exc_info)
        return self.format_combine_lines(lines)
    def format_combine_lines(self, lines):
        return '\n'.join(lines)

class HTMLFormatter(TextFormatter):

    def quote(self, s):
        return html_quote(s)
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

def format_html(exc_data, **ops):
    return HTMLFormatter(**ops).format_collected_data(exc_data)
def format_text(exc_data, **ops):
    return TextFormatter(**ops).format_collected_data(exc_data)

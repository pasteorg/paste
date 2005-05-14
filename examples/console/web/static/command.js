output_html = ''

urllib = importModule('urllib');

function servlet_comm(s) {
  urllib.sendRequest('post',
		     '?_action_=postrun',
		     'command=' + escape(s, true),
		     [['Content-type', 'application/x-www-form-urlencoded']],
		     add_response);
}


function send_command() {
  var command_short = document.getElementById('command');
  var command_long = document.getElementById('command_long');
  var command = command_short.value;
  if (command == '') {
    command = command_long.value;
  }
  if (command == '') {
    return false;
  }
  command_short.value = '';
  command_long.value = '';
  output_html += '<span class="input">&gt;&gt;&gt; '
    + html_quote(command) + '</span>\n';
  servlet_comm(command);
  return false;
}

function add_response(res) {
  var result = res.responseText;
  var command_short = document.getElementById('command');
  if (result != null) {
    output_html += '<span class="output">' 
      + html_quote(result) + '<span>\n';
  }
  refresh_display();
  command_short.focus();
}

function refresh_display() {
  var output_div = document.getElementById('output');
  output_div.innerHTML = output_html;
}

function html_quote(s) {
  return s.replace('&', '&amp;').replace('<', '&lt;');
}

function clear_output() {
  output_html = '';
  refresh_display();
  return false;
}

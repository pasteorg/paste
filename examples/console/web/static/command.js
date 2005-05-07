output_html = ''

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
  var result = servlet.run(command);
  output_html += '<span class="input">&gt;&gt;&gt; '
    + html_quote(command) + '</span>\n';
  if (result != null) {
    output_html += '<span class="output">' 
      + html_quote(result) + '<span>\n';
  }
  refresh_display();
  return false;
}

function refresh_display() {
  var output_div = document.getElementById('output');
  output_div.innerHTML = output_html;
}

function html_quote(s) {
  return s.replace('&', '&amp;').replace('<', '&lt;');
}

function clear() {
  alert(output_html);
  output_html = '';
  refresh_display();
  return false;
}

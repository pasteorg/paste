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
  var output_div = document.getElementById('output');
  output_html += '<br>\n' + '<span class="input">'
    + command + '</span>';
  if (result != nil) {
    output_html += '<br>\n' + '<span class="output">'
      + result + '</span>';
  }
  output_div.innerHTML = output_html;
  return false;
}

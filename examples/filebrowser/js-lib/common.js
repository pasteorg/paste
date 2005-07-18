function jump(anchor) {
  var dest_url = anchor.getAttribute('jumpurl');
  var name = window.prompt('Jump to what file?')
  location.href = dest_url + '?name=' + escape(name);
}

Element.hidden = function() {
  for (var i = 0; i < arguments.length; i++) {
    var element = $(arguments[i]);
    if (element.style.display != 'none') {
      return false;
    }
  }
  return true;
}

function lazyToggle(container, url, options) {
  options = extend({method: 'get'}, options || {});
  if (Element.hidden(container)) {
    Element.show(container);
    if (! $(container).lazy_loaded) {
      new Ajax.Updater(container, url, options);
      $(container).lazy_loaded = true;
    }
    if (options.link) {
      var newHTML = options.link.getAttribute('shownhtml');
      if (newHTML) {
	options.link.setAttribute('hiddenhtml', options.link.innerHTML);
	options.link.innerHTML = newHTML;
      }
    }
  } else {
    Element.hide(container);
    if (options.link) {
      var newHTML = options.link.getAttribute('hiddenhtml');
      if (newHTML) {
	options.link.innerHTML = newHTML;
      }
    }
  }
}

function toggle(container, options) {
  if (Element.hidden(container)) {
    Element.show(container);
    if (options && options.link) {
      var newHTML = options.link.getAttribute('shownhtml');
      if (newHTML) {
	options.link.setAttribute('hiddenhtml', options.link.innerHTML);
	options.link.innerHTML = newHTML;
      }
    }
  } else {
    Element.hide(container);
    if (options && options.link) {
      var newHTML = options.link.getAttribute('hiddenhtml');
      if (newHTML) {
	options.link.setAttribute('shownhtml', options.link.innerHTML);
	options.link.innerHTML = newHTML;
      }
    }
  }
}

/* From: http://www.quirksmode.org/js/cookies.html */

function createCookie(name,value,days)
{
	if (days)
	{
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires = "; expires="+date.toGMTString();
	}
	else var expires = "";
	document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name)
{
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i < ca.length;i++)
	{
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
	}
	return null;
}

function eraseCookie(name)
{
	createCookie(name,"",-1);
}

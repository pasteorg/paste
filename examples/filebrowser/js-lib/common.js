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
  options = ({method: 'get'}).extend(options);
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

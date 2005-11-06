function show_frame(anchor) {
    var framecount = anchor.getAttribute('framecount');
    var expanded = anchor.expanded;
    if (expanded) {
        MochiKit.DOM.hideElement(anchor.expandedElement);
        anchor.expanded = false;
        return false;
    }
    anchor.expanded = true;
    if (anchor.expandedElement) {
        MochiKit.DOM.showElement(anchor.expandedElement);
        return false;
    }
    var url = debug_base
        + '/_debug/show_frame?framecount=' + framecount
        + '&debugcount=' + debug_count;
    var d = MochiKit.Async.doSimpleXMLHttpRequest(url);
    d.addCallbacks(function (data) {
        var el = MochiKit.DOM.DIV();
        anchor.parentNode.insertBefore(el, anchor.nextSibling);
        el.innerHTML = data.responseText;
        anchor.expandedElement = el;
    }, function (error) {
        alert('An error occurred: "' + error + '" for URL: ' + url);
    });
}

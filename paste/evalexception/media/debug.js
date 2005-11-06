function showFrame(anchor) {
    var framecount = anchor.getAttribute('framecount');
    var expanded = anchor.expanded;
    if (expanded) {
        MochiKit.DOM.hideElement(anchor.expandedElement);
        anchor.expanded = false;
        _swapImage(anchor);
        return false;
    }
    anchor.expanded = true;
    if (anchor.expandedElement) {
        MochiKit.DOM.showElement(anchor.expandedElement);
        _swapImage(anchor);
        $('debug_input_'+framecount).focus();
        return false;
    }
    var url = debug_base
        + '/_debug/show_frame?framecount=' + framecount
        + '&debugcount=' + debug_count;
    var d = MochiKit.Async.doSimpleXMLHttpRequest(url);
    d.addCallbacks(function (data) {
        var el = MochiKit.DOM.DIV({});
        anchor.parentNode.insertBefore(el, anchor.nextSibling);
        el.innerHTML = data.responseText;
        anchor.expandedElement = el;
        _swapImage(anchor);
        $('debug_input_'+framecount).focus();
    }, function (error) {
        showError(error.req.responseText);
    });
    return false;
}

function _swapImage(anchor) {
    var el = anchor.getElementsByTagName('IMG')[0];
    if (anchor.expanded) {
        var img = 'minus.jpg';
    } else {
        var img = 'plus.jpg';
    }
    el.src = debug_base + '/_debug/media/' + img;
}

function submitInput(button, framecount) {
    var input = $(button.getAttribute('input-from'));
    var output = $(button.getAttribute('output-to'));
    var url = debug_base
        + '/_debug/exec_input';
    var vars = {
        framecount: framecount,
        debugcount: debug_count,
        input: input.value
    };
    MochiKit.DOM.showElement(output);
    var d = MochiKit.Async.doSimpleXMLHttpRequest(url, vars);
    d.addCallbacks(function (data) {
        var result = data.responseText;
        output.innerHTML += result;
        input.value = '';
        input.focus();
    }, function (error) {
        showError(error.req.responseText);
    });
    return false;
}

function showError(msg) {
    var el = $('error-container');
    if (el.innerHTML) {
        el.innerHTML += '<hr noshade>\n' + msg;
    } else {
        el.innerHTML = msg;
    }
    MochiKit.DOM.showElement('error-area');
}

function clearError() {
    var el = $('error-container');
    el.innerHTML = '';
    MochiKit.DOM.hideElement('error-area');
}

function expandInput(button) {
    var input = button.form.elements.input;
    stdops = {
        name: 'input',
        style: 'width: 100%',
        autocomplete: 'off'
    };
    if (input.tagName == 'INPUT') {
        var newEl = MochiKit.DOM.TEXTAREA(stdops);
        var text = 'Contract';
    } else {
        stdops['type'] = 'text';
        var newEl = MochiKit.DOM.INPUT(stdops);
        var text = 'Expand';
    }
    newEl.value = input.value;
    newEl.id = input.id;
    MochiKit.DOM.swapDOM(input, newEl);
    newEl.focus();
    button.value = text;
    return false;
}

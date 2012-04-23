String.prototype.format = function() {
    var formatted = this;
    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{'+i+'\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    return formatted;
};

function tooltip(apply_for) {
    if (typeof apply_for == 'undefined' ) apply_for = $(".tooltip");
    apply_for.tooltip({
        delay:1000,
        showBody:" : ",
        showURL:false
    });
};
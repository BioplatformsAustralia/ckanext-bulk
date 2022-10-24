// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('bulk_download_popover', function ($) {
  return {
    initialize: function () {
      $.proxyAll(this, /_on/);

       // Access some options passed to this JavaScript module by the calling
      // template.;
      var title = this.options.title;
      var wording = this.options.wording;
      var url = this.options.url;
      var visible = false;

      var content = 'WORDS   <a class="btn btn-primary fa fa-download" href="URL"> Download Zip</a>'
        .replace('WORDS', wording)
        .replace('URL', url)

      // Add a Bootstrap popover to the HTML element (this.el) that this
      // JavaScript module was initialized on.
      this.el.popover({title: title,
                       html: true,
                       content: content,
                       placement: 'top',
                       trigger: 'focus'});

    },
    _popover_visible: true,

    _onClick: function(elem) {;
       // Wrap this in an if, because we don't want this object to respond to
      // its own 'dataset_popover_clicked' event.
      if (this.el.length > 1) {
              console.log("not eqiual, go and hide it");

      }
    },

  };
});
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
      var bulk_title = this.options.title;
      var bulk_wording = this.options.wording;
      var bulk_url = this.options.url;

      var bulk_content = 'WORDS  <a class="btn btn-primary popover-btn fa fa-download pull-right" href="URL"> Download Zip</a>'
        .replace('WORDS', bulk_wording)
        .replace('URL', bulk_url)

      // Add a Bootstrap popover to the HTML element (this.el) that this
      // JavaScript module was initialized on.
      this.el.popover({title: bulk_title,
                       html: true,
                       content: bulk_content,
                       placement: 'top',
                       trigger: 'focus'});

    },
  };
});
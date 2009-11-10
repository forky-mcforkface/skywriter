/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1
 *
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied.
 * See the License for the specific language governing rights and
 * limitations under the License.
 *
 * The Original Code is Bespin.
 *
 * The Initial Developer of the Original Code is Mozilla.
 * Portions created by the Initial Developer are Copyright (C) 2009
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Bespin Team (bespin@mozilla.com)
 *
 * ***** END LICENSE BLOCK ***** */

var settings = require("bespin/settings");

/**
 * URLBar watches the browser URL navigation bar for changes.
 * If it sees a change it tries to open the file
 * The common case is using the back/forward buttons
 */
var last = document.location.hash;

/**
 * Once everything is going, scan the URL bar periodically
 */
exports.monitor = function() {
    window.setInterval(function() {
        var hash = document.location.hash;
        if (last != hash) {
            bespin.publish("url:changed", {
                was: last,
                now: new settings.URL(hash)
            });
            last = hash;
        }
    }, 200);
};

/**
 * Grab the setting from the URL, either via # or ?
 */
exports.URL = SC.Object.extend({
    init: function(queryString) {
        this.results = util.queryToObject(this.stripHash(queryString || window.location.hash));
    },

    getValue: function(key) {
        return this.results[key];
    },

    setValue: function(key, value) {
        this.results[key] = value;
    },

    stripHash: function(url) {
        var tobe = url.split('');
        tobe.shift();
        return tobe.join('');
    }
});

This example implements an interactive Python shell in the browser.
This uses "Ajax" style interaction, where entering a command sends the
command in the background to the server, and updates the application
in-place with the response.

This uses jsolait for the server communication: http://jsolait.net/
You must download that library and put it in web/jsolait

This must be run from a threaded server, as state is kept in a module
global.  Potentially it could be run out of the session, but many
objects you may want to manipulate can't be pickled.  Another option
would be a single process that does the execution, which the web
frontend would communicate, but that's more complicated to set up.

Access is restricted to 127.0.0.1 (localhost) for obvious security
reasons.


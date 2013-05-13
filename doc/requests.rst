===================
Request File Format
===================

Train needs a way to generate the requests that are fed to the
middleware.  These requests are set up through one or more request
files, which have the file format documented here.  Each request is a
member of a *sequence*; sequences provide an ordering of requests and
enable the insertion of time gaps into the sequence.  The request
files are composed of one or more sequences, and the requests for a
given sequence can be split across multiple files.  Conceptually, a
sequence corresponds to one logical client accessing the service, and
the use of multiple sequences allows for the illusion of several
clients accessing the service simultaneously.

Requests, of course, consist of an HTTP method, the URI accessed, and
a set of headers on the request.  As a convenience, headers may also
be set on the sequence itself, or at the global scope; these
convenience headers are inherited at each request, but may be deleted
or modified as desired.  Note that the convenience headers are
per-file only, even though a given sequence may be spread across
multiple files.

Scopes
======

To understand the request file format, the first concept to understand
is the three different kinds of header *scope*: *global* scope,
*sequence* scope, and *request* scope.

Global Scope
------------

The global scope is simply the scope at the beginning of the request
file, prior to any sequence definitions.  Headers defined here are
inherited by every request in the request file.  An empty section
header (i.e., "[]") can also be used to introduce the global scope
later in a file; this allows inherited header values to be changed for
all following requests.

Sequence scope
--------------

Sequence scope is introduced by a section header, e.g., "[client1]".
Any headers defined prior to the first request in the sequence scope
will be inherited by all following requests.  (Note that, after a
request is defined in the sequence scope, the scope becomes the
request scope, and the section header must be repeated to alter the
inherited header values.

Request Scope
-------------

Requests can only be declared following a section header.  They
consist of an HTTP method, followed by the URI path for the request;
for example, "GET /".  A request declaration switches to the request
scope, and all headers following the request declaration apply
specifically to that request.

Headers
=======

Headers are declared in the request file using a straight-forward
syntax: the header name, followed by a colon, followed by the value of
the header.  Header values are normalized (all sequences of whitespace
are converted into a single space character, and whitespace is
stripped from the beginning and ending of the value), and header
continuation as per the HTTP specification is honored.  For example,
the following sets the HTTP header "X-Train-Test" to the value "this
is a test"::

    X-Train-Test: this        is
        a test

Note that header names are not sensitive to case; further, the dash
character ("-") and the underscore character ("_") are considered
equivalent, so the header "x-train-test" is equivalent to
"X_TRAIN_TEST".

Unlike the HTTP specification, repeating a header does not append the
value to the previous value; instead, the header value is replaced.
This can be useful to override the value of a global- or
sequence-scope header for a request, or to alter the value at global
or sequence scope.

It is also possible to delete a header by preceding the header name
with a single "-", i.e., "-X-Train-Test".  This deletion is honored
regardless of the scope, so placing this at sequence scope overrides
any setting at global scope for the remainder of that sequence, and
similarly for header deletions at request scope.

Finally, overrides for any header may be reset by preceding the header
name with a "!", i.e., "!X-Train-Test".  This undoes any header value
override or deletion at the current scope, and restores the inherited
value of that header (if any) from the parent scope.

The following is an example of these header manipulation operations::

    X-Train-Test: this is a test

    [client1]
    -X-Train-Test

    GET /
    # For this request, there will be no X-Train-Test header.

    GET /
    !X-Train-Test
    # For this request, there still will be no X-Train-Test header;
    # all the reset does is reset any overrides within this scope, not
    # within the parent scope.

    [client1]  # Resets the scope to sequence scope.
    !X-Train-Test

    GET /
    # For this request, X-Train-Test has the value "this is a test".

    GET /
    -X-Train-Test
    # For this request, we have explicitly deleted the X-Train-Test
    # header, so it will not be present.

    GET /
    # For this request, X-Train-Test will again be present, since this
    # is a different request and thus a different scope.

Requests and Gaps
=================

As described above, requests are declared by simply specifying the
HTTP method and the URI, and following the declaration by any HTTP
headers (or header manipulation operations).  Each request is
fed to the service in sequence; however, the requests are fed in so
fast that they may be considered simultaneous.  To combat this, it is
possible to declare a time gap within the sequence.  The time gap is
declared as a "+" followed by the gap length, in seconds; this gap is
interpreted as a floating point number, so fractional seconds are
possible.  As an example::

    [client1]
    GET /

    +2.5  # Introduce a gap of 2 and 1/2 seconds

    GET /

One note regarding gaps--they separate requests and switch processing
back to the sequence header scope::

    [client1]
    GET /  # No headers (or headers inherited from the global scope).
    +2.5
    X-Train-Test: this is a test

    GET /  # This will have the X-Train-Test header set.

Comments
========

It should be obvious, from the above examples, that the "#" character
introduces comments.  However, URIs may also contain the "#"
character, as it identifies URI fragments.  To work around this, the
"#" character is treated as a comment only if it occurs in the
left-most column or is preceded by whitespace.  For example::

    # Occurs in the left-most column, so this is a comment.

     # Preceded by whitespace, so this is also a comment.

    []  # Since "#" is preceded by whitespace, this is also a comment.

    # The "#" below does *not* introduce a comment.
    GET /test/document#fragment

Multiple Files
==============

Multiple request files may be read.  The sequence names from each file
are matched up, and the requests are appended in file order; that is,
if 2 requests are read from the "client1" sequence of the first file,
and 3 more requests are then read from the "client1" sequence of the
second file, the sequence "client1" will be composed of 5 requests
total, with the 2 read from the first file being at the beginning of
the sequence.  On the other hand, inheritable headers--that is, those
headers occurring at global or sequence scope--are in effect only for
the duration of a single request file.  This ensures that the request
files are independent, allowing the request files to be reordered
without having to worry about which headers are inherited by which
requests.

matnapack
=========

Packing a set of .m MATLAB files from the global namespace into +somenamespace
folder. Packing procedure will also include step on injecting the
'import somenamespace.*' statement into every modified function. Project acts
as a kind of compiler for putting matlab code into namespace scope.

Usage example
-------------

The following example shows how to apply matnapack tool to pack DIP image toolbox (http://www.diplib.org/) into a +dipimage namespace.

1. Place files of interest into newly created +dipimage folder
2. cd +dipimage
3. matnapacker --namespace dipimage --folder-path ./

Use dry-run option for debugging.

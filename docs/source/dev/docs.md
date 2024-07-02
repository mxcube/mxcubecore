# Working with documentation

This documentation is automatically built and published from the contents of the [mxcubecore](https://github.com/mxcube/mxcubecore) repository.
Each time the repository's `develop` branch is updated, documentation is regenerated and published to [https://mxcubecore.readthedocs.io/](https://mxcubecore.readthedocs.io/)

If you want to modify this documentation, make a pull request to the repository with your suggested changes.

## Modifying the documentation

This documentation is built using the [Sphinx](https://www.sphinx-doc.org/) documentation generator.
The documentation's source and configuration files are located in the `docs` folder of the [mxcubecore](https://github.com/mxcube/mxcubecore) repository.
Sphinx will also read [Python docstrings](https://peps.python.org/pep-0257/) from the repository's source code.

Refer to the {doc}`contributing guidelines </dev/contributing>`.


### Building documentation

Follow the instructions for [Installing a development environment](https://mxcubeweb.readthedocs.io/en/latest/dev/environment.html).
The development environment will include Sphinx and all necessary packages for building documentation.

```{attention}
The installation instructions linked above are written for MXCuBE-Web,
but should mostly apply equally well for MXCuBE-Core.
```

Once you have a working environment, use these commands to build the documentation:

    # goto docs folder
    $ cd docs

    # build documents with Sphinx
    $ make html

The commands above will generate documentation in `docs/html/` directory.
The generated docs can be viewed by opening `docs/html/index.html` in your web browser.


## More details about documentation system

The documentation system is built around [Sphinx](https://www.sphinx-doc.org/).

There is a `Makefile` in the `docs` directory,
that allows building the documentation with a simple command like the following:

```none
make html
```

But the actual build is performed by the `sphinx-build` program.
From the root of the project,
a command like the following should build the HTML documentation:

```none
sphinx-build -M html docs/source docs/build -c docs
```

The theme used is [*furo*](https://pypi.org/project/furo/).

### Markup

The default markup language for Sphinx is
[*reStructuredText*](https://docutils.sourceforge.io/rst.html).
The [usage of *Markdown*](https://www.sphinx-doc.org/en/master/usage/markdown.html)
to write documents is enabled via
[*MyST*](https://myst-parser.readthedocs.io/).
Note that for special Sphinx features such as *roles*, *directives*, and so on,
the Sphinx documentation focuses on the Restructuredtext notation only.
To learn how to use these features in Markdown documents,
one should refer to the MyST documentation.
The docstrings in Python code are still to be written with Restructuredtext syntax, though.

### Python code

The documentation system is configured to generate {doc}`API documentation </dev/api>`
based on the Python code.
The Sphinx extension used to do this is
[*`autosummary`*](https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html).
This extension imports (or even runs?) the code in order to do its work.

The
[*`napoleon`*](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
extension is enabled to handle docstrings within the Python code
and it is configured for
[Google-style docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings).

### Diagrams

The
[*`sphinxcontrib-mermaid`*](https://pypi.org/project/sphinxcontrib-mermaid)
extension is enabled to allow embedding [*Mermaid* diagrams](https://mermaid.js.org/)
in the documentation.

For example the following code in a Markdown document:

~~~markdown
```{mermaid}
sequenceDiagram
participant Alice
participant Bob
Alice->John: Hello John, how are you?
```
~~~

or the following in a ReStructuredText document:

```restructuredtext
.. mermaid::

    sequenceDiagram
    participant Alice
    participant Bob
    Alice->John: Hello John, how are you?
```

produce the following diagram:

```{mermaid}
sequenceDiagram
participant Alice
participant Bob
Alice->John: Hello John, how are you?
```

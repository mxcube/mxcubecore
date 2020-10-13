## How to contribute to HardwareRepository of MXCuBE

Before submiting the code to the repository please read these contributing guidlines.
The aim of these guidlines is to help the developers community to maintain the code stable and reusable.

### Reporting bugs

Before submitting a new bug check if the bug is not already reported in the [issues](https://github.com/mxcube/HardwareRepository/issues/).
If the corresponding issue do not exist then:

* Open a new issue with a short description in the title.
* In the description describe the bug:
    * Conditions when the bug appears.
    * How it can be reproduced.
    * Possible cause of the bug and source code where it occures.
    * If possible add error log and screenshot.
* Assign a label to the issue (see available labels).

### Submiting code to the repository

Pull request (PR) is the most convinient way of submitting a new code to the repository. It helps developers to see the proposed code and publicly review it. To avoid any conflicts in the code base it is important to keep your local git repository syncronized with the latest code in the repository. If repository is checkout out directly then use `git pull` to obtain the latest code from the repository. If a local fork is used then:

* If necessary add link to the upstream repository:

  ```bash
  git remote add upstream https://github.com/mxcube/HardwareRepository.git
  ```

* Fetch all branches and merge upstream to your forked master:
  ```bash
  git fetch --all
  git checkout master
  git merge upstream/master
  ```

#### Preparing a new commit

* Create a new branch:
  `git checkout -b NEW_BRACH_NAME`
  * If the pull request is associated with an issue then reference the issue in the name. For example:
  `git checkout -b issue_100`
* Edit necessary files, delete existing or add a new file.
* Add files to the staging area:
   `git add ChangedFile1 ChangedFile2`
* Save your new commit to the local repository:
   `git commit`                          
* Commit command will open a text editor:
  * In the first line write a short commit summary (max 50 characters. It will appear as a title of PR.
  * Add an empty line.
  * Write a longer description.
* Upload the content of the new branch to the remote repository:
   `git push origin NEW_BRACH_NAME`
* Go to the github webpage and create a new PR.

#### Anouncing a new pull request via github webpage

* Go to the project webpage and press "Create pull request".
* Edit information about the PR.
* If needed assign a developer who shall review the PR.

### Accepting a pull request

* The author of a PR may request a PR review from a certain amount of developers.
* A reviewer can Comment, Approve or Request changes.
* Before accepting the PR reviewer has to test the proposed code changes. To test the PR pull the proposed PR and run mxcube:
  ```bash
  git fetch origin pull/ID/head:NEW_BRANCH_NAME
  git checkout NEW_BRANCH_NAME

  start mxcube
  ```
* All the assigned reviewers of a PR have to approve the PR before it can be merged.
* The last reviewer to review the PR have the responsibility of merging it.
* A PR that has no reviewer can be approved and merged by anyone.

### Coding convention

## Units
Functions return a value representing a physical quantity should in general be assoicated with 
a unit. It has been agreed that the following units should, where applicable, be used across the 
code base

 * mm (millimeter) for translative motors and sizes
 * degrees for rotative motors
 * perecent (%) for ratios like attenuation
 * keV for energy
 * K (Kelvin) for temperature
 * Å (Ångström) for resolution
 * Pixels are to be used for beam location (center)
 * Datetime YYYY-MM-DD HH:MM:SS possible with hundreds of seconds and with 24 hour clock

## Value update signals/callbacks
The "valueChanged" and "stateChanged" signals should be used when a HardwareObjects value or state
has been changed. Defined in for instance the base class [HardwareObject](https://github.com/mxcube/HardwareRepository/blob/ea8369ab2c08dbe539fd92ffee18fd21bb3a81b8/BaseHardwareObjects.py#L666), [AbstractMotor](https://github.com/mxcube/HardwareRepository/blob/master/HardwareObjects/abstract/AbstractMotor.py) and 
[AbstractActutor](https://github.com/mxcube/HardwareRepository/blob/master/HardwareObjects/abstract/AbstractActuator.py)

The use of the the signal "attributeChanged" with a key, value pair is encouraged for all other 
attributes, for instance ```self.emit("attributeChanged", "attr1", 0)``` instead of using a 
specific signal with for instance a single dictionary as data.

## Naming convention

# Functions
  * functions names should generally contain a verb

# Variables and parameters:
 * names of objects and values are singular
 * names of collections and maps are plural or contain 'map', 'dict','data', or an internel '2', like 'name2state'
 
 
### Coding style guidlines

It is very important to write a clean and readable code. Therefore we follow the [PEP8 guidlines](https://www.python.org/dev/peps/pep-0008/). Minimal required guidlines are:
* Maximum 88 characters per line.
* Use 4 spaces (not a tab) per identation level.
* Do not use wild (star) imports.
* Used naming styles:
   * lower_case_with_underscores (snake style) for variables, methods.
   * CapitalizedWords for class names.
   * UPPERCASE for constants.
* When catching exceptions, mention specific exceptions whenever possible instead of using a bare except.
* Add [google style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html?highlight=google%20style) doc strings to describe methods and classes:

An example how to describe a class:

  ```bash
class ExampleClass(object):
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Properties created with the ``@property`` decorator should be documented
    in the property's getter method.

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """

    def __init__(self, param1, param2, param3):
        """Example of docstring on the __init__ method.

        The __init__ method may be documented in either the class level
        docstring, or as a docstring on the __init__ method itself.

        Either form is acceptable, but the two should not be mixed. Choose one
        convention to document the __init__ method and be consistent with it.

        Note:
            Do not include the `self` parameter in the ``Args`` section.

        Args:
            param1 (str): Description of `param1`.
            param2 (:obj:`int`, optional): Description of `param2`. Multiple
                lines are supported.
            param3 (list(str)): Description of `param3`.

        """
        self.attr1 = param1
        self.attr2 = param2
        self.attr3 = param3  #: Doc comment *inline* with attribute

        #: list(str): Doc comment *before* attribute, with type specified
        self.attr4 = ['attr4']

        self.attr5 = None
        """str: Docstring *after* attribute, with type specified."""

  ```

An example how to describe a function:

  ```bash
def function_with_types_in_docstring(param1, param2):
    """Example function with types documented in the docstring.

    `PEP 484`_ type annotations are supported. If attribute, parameter, and
    return types are annotated according to `PEP 484`_, they do not need to be
    included in the docstring:

    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.

    .. _PEP 484:
        https://www.python.org/dev/peps/pep-0484/

    """

  ```



You can use [autopep8](https://pypi.org/project/autopep8/) and [black](https://pypi.org/project/autopep8/) to format your code:

  ```bash
  autopep8 -a -r -j 0 -i --max-line-length 88 ./
  black --safe ./
  ```

### Continuous integration (CI)

For continuous integration [Travis](https://travis-ci.org/) is used.

### Additional notes

Issue and Pull request Labels

* bug: indicates a bug in the code. Issue has a highest priority.
* abstract: Abstract class involved. Issue has a hight priority.
* question: general question.
* not used code: suggestion to remove a code block or a file from the repository.
* wip: work in progress
* enchancement: code improvement.

Milestones

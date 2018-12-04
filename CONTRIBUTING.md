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

Pull request (PR) is the most convinient way of submitting a new code to the repository. It helps developers to see the proposed code and publicly review it. You may submit a new PR from your forked repository or from a branch.

#### Preparing a pull request from a forked repository

* Update your code to the latest code available on the master branch:
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
* Edit necessary files, delete existing or add a new file.
* Add files to the staging area:
   `git add ChangedFile1 ChangedFile2`
* Save your new commit to the local repository:
   `git commit`
* Upload the content of your repository to the remote repository:
   `git push origin master`
* Go to the github webpage and create a new PR. 

#### Preparing a pull request from a branch

* Update your code to the latest code available on the master branch:
  `git pull`
* Create a new branch:
  `git checkout -b NEW_BRACH_NAME`
  * If the pull request is associated with an issue then reference the issue in the name. For example:
  `git checkout -b issue_100`
* Edit necessary files, delete existing or add a new file.
* Add files to the staging area:
   `git add ChangedFile1 ChangedFile2`
* Save your new commit to the local repository:
   `git commit`                          
* Upload the content of the new branch to the remote repository:
   `git push origin NEW_BRACH_NAME`
* Go to the github webpage and create a new PR.

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

You can use [autopep8](https://www.python.org/dev/peps/pep-0008/a/) and [black](https://pypi.org/project/autopep8/) to format your code:

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

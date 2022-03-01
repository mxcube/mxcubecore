	Title: Development and release guidelines
	MEP: 1
	State: CANDIDATE
	Date: 2022-02-28
	Drivers: Rasmus Fogh, Marcus Oscrasson
	URL:
	Abstract:
	This MEP describes how to create releases for the mxcubecore package by adopting
      a tag schema compliant with PEP440. It is a further development of the original
      gitflow proposal by Jordi Andreu, as refined by the mxcube developers, inspired 
      by the oneflow workflow. It deviates from the latest consensus (hopefully in a
      way that will simplify the work), particularly in reducing and simplifying the 
      versioning scheme.
      


Introduction
============

While reaching the last part of the massive refactoring of the HardwareRepository 
(renamed to `mxcubecore`), and with the aim to converge again the code in all sites, 
it has been realized the need to adopt of a robust version model and release strategy in
order to easily track the version of the library, being the core library for the MXCuBE
`web` and `qt` applications.

This version is based on recent discussions among the MXCuBE developers, and inspired 
by the oneflow workflow. It proposes a simplified versioning model, that is 
consisent with semantic versioning.


Out of scope
============
The mechanism (manual or automated) to create the library package for each release and
its upload to a software repository is out of the scope of this proposal.

This proposal (like the oneflow model) covers the situation where each release 
follows from the preceding one, in a linear fashion. Long-lived, parallel release branches
(like Python 2 v. Python 3), are not well catered for - and may well be a problem with
no solution. There is a risk that we may run into similar situations with beamline-specific
versions, or versions using different front ends, and such cases will have to be
dealt with ad-hoc. This system also does not allow for making either releases or patches 
anywhere but at the newest release; i.e. you cannot make release 2.2.1 after 2.3.0 is 
released, or 2.4.0 after 3.0.0 is released. 


Glossary
========

- `master branch:` The permanent main branch that is checked out by default. Used solely for holding tagged releases.

- `develop branch` The permanent branch used to gather all changes in MXCuBE and serve as the starting point for releases. 

- `Release:` The distribution of a certain (final) version of an application.

- [Release Lifecycle:](https://en.wikipedia.org/wiki/Software_release_life_cycle) Set of
  actions involved in the creation of a new piece of software.


Prior situation (previous to MEP1)
====================================
The [canonical repository](http://www.github.com/mxcube/mxcubecore) is hosted at 
`github.com` under the `mxcube` organization. Current development guidelines are based
on the so called [GitHub flow](https://guides.github.com/introduction/flow/). We use a
single `master branch` to merge any `feature branch` by the mechanism of creating a PR and
its acceptance after review. There is no versioning model defined nevertheless, some
code releases have been documented using the release tag feature from GitHub.

The MXCuBE project is currently under a massive refactoring of the `mxcubecore` library.
Although the amount of code that has been already refactored is non-negligible, we
still foresee important changes in the API defined so far. This fact together with the
need to easily track the version of the library used at each different site, makes the
adoption of a versioning model a tool to effectively address this challenges.


Goals & considerations
======================

The following lists the main goals taken into consideration for this proposal:

1. A release schema has to provide a clear versioning of the code at different stages.
   This will facilitate the identification of the code used at any time.

2. Each release should provide a comprehensive list of changes with all additions and 
   changes.
  
3. Any non-backward compatible change on the code must be discussed and agreed by the 
   developers, any new feature must be backward compatible with the existent code and 
   any bug fix must be also be backward compatible.

4. We need to adopt development and release guidelines according to the project nature:
   code need to be tested with site-specific hardware and is difficult to perform functional
   tests covering most of the scenarios.
5.  The scheme should be as simple in everyday use as possible, to maximise compliance.
  

Implementation
==============

This section presents some technical solutions and tools proposed to achieve the proposed
goals:

## Development guidelines

We propose the adoption of the [oneflow workflow](https://www.endoflineblog.com/implementing-oneflow-on-github-bitbucket-and-gitlab),
two-branch variant. We can summarize the most important procedures in this model as:

- The `master branch`, which is the one checked out by default, serves only to collect successive releases.
  Releases are merged to the master branch, and rebasing or cherrypicking is not allowed.

- The (permanent) `develop branch` Tracks the (linear) development of the project and is the only starting point for releases.
  Changes are merged to the develop branch, and rebasing or cherrypicking is not allowed.

- Each new feature is implemented in a temporary `feature branch`, branching from the `develop branch`.

- The merge of a `feature branch` is made via PR to the `develop branch`. The author of 
  the PR must solve any conflicts with the latest development version before the merge,
  by rebasing the feature branch on the develop branch.

- When decided, a `release branch` is created from the `develop branch` and becomes
  a release candidate version.

- Once the code can be released, the release branch is merged to the `master branch` and
  also to the `develop branch`.
  
- If a bug is found in a released version, a `hotfix branch` is created with the 
  necessary changes and the completed fix is merged to the `master branch` and
  also to the `develop branch`.



## Versioning guidelines

The general schema described in the [PEP440](https://www.python.org/dev/peps/pep-0440/):
  is highly powerful and flexible, and in this problably superior to the more common 
  [semantic versioning](https://semver.org/). Nevertheless it is unavoidably complex
  and labour intensive to keep and track a seperate version for every commit in the
  `develop` branch. The scheme presented here applies semantic versioning, but 
  *only to the actual releases* with their associated `release` and `hotfix` branches.
  After all, how often do you need an external and reliable reference to a specific
  non-released commit (beyond, of course, the git commit hash)?

- We will use the segments `major.minor.patch` to assign a version released from the
  `master branch`, following semantic versioning. Changes that break the API require
  a major version change, changes that add features require a minor version change, and
  other changes require patch changes. Changes that only affect a single beamline are
  treated as neutral; so are changes that only affect the GPhL workflow, until such a 
  time that the workflow is adopted for production use.
- We will store in the code (location to be decided) a matching version string, which 
  outside of tagged releases will refer to the version of the *most recent prior release* 
  among the ancestors of the present commit. This is the *Bumpversion model* (see below).
- Version bumping will *only* take place as part of the release procedure.
- Distinctions between successive commits, and between develop, release candidate and 
  hotfix candidate commits will be done using the branch structure and commits of the 
  git repository.
- The decision whether a new release is breaking (-> bump major version) or non-breaking
  (-> bump minor version) has to be taken at release time. To avoid errors we shall
  have to rely on updating release notes at each commit, noting explicitly when we have
  a breaking change.


### Bumpversion model
We will use [bumpversion](https://github.com/c4urself/bump2version) as a
tool to track the different versions. In this case, `bumpversion` assumes that the version
string is writen in (at least) one project file. When bumping the version, `bumpversion`
will search for the current version string, will calculate the next version
according to the segment to bump and will replace the old version string by the new one.
We will not use bumpversion to tag the repository, since the tagging needs to be done after the bump.
 

## Keep track of the repository changes

A `changelog` file should be used to track the changes of the different versions released.
This will require a dedicated commit on the corresponding branch.

We propose to follow the guidelines from [keepachangelog](https://keepachangelog.com/en/1.0.0/).
The changelog file will be updated manually before each merge commit the following situations:

- Adding an entry at the `Unreleased` changes section of the changelog when merging any
  feature branch to the develop branch. It is crucial that breaking changes are clearly
  signalled at this point, in order to guide the generation of the next release.
  
- Moving the content of the `Unreleased` section to a new `Release` section in the 
  changelog as part of the release procedure.

All changes in a release will be grouped using the most appropriate category from the 
recommended list: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` and `Security`.

## Procedures

Procedures are taken from [oneflow](https://www.endoflineblog.com/implementing-oneflow-on-github-bitbucket-and-gitlab#feature-branches), 
adapted to our versioning scheme. More details can be found on the oneflow page

### Feature branches

These are temporary branches that serve to make a new feature and edit it until it can be merged into 
the `develop branch`

#### Starting a feature branch

$ git checkout -b my-feature develop

$ git push -u my-fork my-feature

Feature branches can be named freely. It is recommended to create the name from your 
name and a descriptive title such as `rhf/add_gphl_ui`.

You can add new commits freely as you work on the feature, and push them to your fork

$ git push

or

$ git push -f my-fork my-feature

It is recommended to periodically rebase your feature branch on develop.

#### Finishing a feature branch

When you are ready to merge in your feature, you rebase on develop and make a pull request.


Edit the release notes, adding the changes from your feature to the `Unreleased` list, 
and commit the result.

$ git fetch origin

$ git checkout my-feature

$ git rebase origin/develop

$ git push -f my-fork my-feature

Now you can make the pull request.
You add additional commits and push them as necessary until the pull request is accepted.

After the pull request is accepted and merged in, you should delete the feature branch

There are three ways to do the merges into develop, which presumably have to be set in
the git repository. I would recommend the following (Option #3 from oneflow):

`merge --no-ff`

This will add a merge commit for every feature merge, so the feature can be undone in a 
single operation. It will keep a nice, linear commit graph, *provided* all users
remember to rebase before merging, as above. Alternatives are:

`rebase / merge --ff-only`  (Option #1 from oneflow)

This will add the individual commits from the feature to the tip of the `develop branch`
without a merge commit

`merge --squash`   (Option #2 from oneflow)

This will collapse the feature commits into a single commit, and put that on the tip of the develop branch.

### Release branches

Release branches must be started from a commit on the `develop branch`. It need not be the tip
(though it mostly will be), but it must be subsequent to any previous release.

Release branches are named as proposed by oneflow. This is not teh only possibility, 
but is a clear and visible way to signal that this is a release branch. It avoids 
the 'rc0' etc. suffixes, since we are not versioning the individual commits.

$ git checkout -b release/2.3.0 develop   # If you want a specific commit check out that instead

$ git push origin release/2.3.0

Now edit the release notes, and bump the internal version string. Be careful to note
(from the release notes) whether this is a breaking change (requiring a major version 
bump) or not. Commit the result.

As you modify the release, make PRs (or push) the changes to the origin repository. 
The merge options are the same as for feature branches.

When the release is ready it should be tagged and merged. It is simpler to do this in raw
git, rather than thorugh Pull Requests - anyway there should be agreement on the final 
form before we get to this point. Note that if you made a PR at this point you would
need to do a bit more gymnastics (see oneflow). So you do:

$ git checkout release/2.3.0

$ git tag 2.3.0

$ git checkout develop

$ git merge release/2.3.0

$ git push --tags origin develop

$ git branch -d release/2.3.0

Followed by

$ git checkout master

$ git merge --ff-only 2.3.0

$ git push origin master

Note that at this point, the internal version tag (that was bumped at the start of 
making the release branch) will have been merged into the develop branch, so that
the develpo branch internal tag reflects the version of the last release.

### hotfix branches

A hotfix branch must begin as a fork from the latest release on the master branch.
Hotfix branches by definition do not break the API or add features, so the new tag
always increases the patch level. The naming of the hotfix branches should be e.g. 
`hotfix/2.3.1` (an alternative would be `patch/2.3.1`). Apart from these points,
hotfix branches are treated exactly liek release branches.
  
License
=======

The following copyright statement and license apply to MEP1 (this
document).

Copyright (c) 2021 Jordi Andreu Segura

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Changes
=======

2021-05-03
[Jordi Andreu](https://github.com/jordiandreu/): Creation of MEP1

2022-01-25
[Rasmus Fogh](https://github.com/rhfogh/): Added section "Version numbers and their interpretation".

2022-03-01
[Rasmus Fogh](https://github.com/rhfogh/): Major rewrite, changing and simplifying
the versioning system, adding detailed commands, and moving from gitflow to oneflow.

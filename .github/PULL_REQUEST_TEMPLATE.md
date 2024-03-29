Please use this PR template for new features, or an abbreviated version for smaller bug fixes and changes.

### Branch name

- [ ] Does your branch name follow the naming convention: [fix,feat,task,bug]/[task-label]
      (ex: feat/new-share-implementation)

### Title

- [ ] Does your PR title reference a ticket, and a short description?
      (ex: EN-10, EN-11 - New share implementation + Improvements)?

### Testing and Pre-Commit

- [ ] Did you merge with the latest main branch? (Run `git pull origin main`)
- [ ] Did you resolve all pre-commit issues? (Run `pre-commit run -a`)
- [ ] Did the unit tests pass? (Run `make test`)

### Description

- [ ] (Optional) - By default, a push to `main` will result in a `patch` version bump (see https://semver.org/). bump minor or major versions. You can
      bump minor or major versions by adding either `+semver: minor` or `+semver: major` to your description

- [ ] Write a simple description, adding enough information to explain what this new feature does

- [ ] Use lists for all tasks the PR does

- [ ] Add a list for things that still need to be done in the current version, or in future versions

- [ ] If applicable: Add screenshots and recordings to show what you saw on your end before sending to others to review.

### Details

- [ ] Critical code must have unit testing
- [ ] Backend code should use asyncio / non-blocking code if it is in a web path
- [ ] Function, variable, and class names are clear and intuitive
- [ ] Comments and annotations are clear and useful, and mostly explain "why" instead of "what"

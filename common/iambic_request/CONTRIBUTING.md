## Foundational Classes

### IambicRepo

IambicRepo is used to create a branch, update a branch, and delete a branch.
This includes checking out the repo, making trees, cleaning up trees and refreshing the repo dir
In other words IambicRepo is the interface to the repo itself and the branches

### BasePullRequest

BasePullRequest is a PR interface base class inherited by supported Git Providers. Currently this is only github.
It is meant to represent a PR in a way meaningful to the new SaaS/Iambic request.

## Flows

### When a request is created

- A Noq Request is created including its UUID
- A PR Instance is created providing the request details and the git provider details
- create_request is called on the PR Instance which creates the branch and PR
- If the repo had never been checked out before, the repo is checked out
- The PR Id is updated on the instance
- The Noq Request is updated to include the PR ID and potentially other metadata about the PR.

### When a request is made to view the request details

- An instance of the ProviderPullRequest is created with the Request PR metadata.
- Call ProviderPullRequest.get_request_details() which returns a dict of the PR details

### When a request is updated (Any changes or the approval of a request)

- An instance of the ProviderPullRequest is created with the Request PR metadata.
- Call ProviderPullRequest.update_request(...) to update the PR with the new changes.
- The call will also update the IambicRepo instance with the new changes.

## Issues

- The hope was to leverage the comments on the PR but that may be difficult because there is no way to add comments
- Repo.clone_from requires a uri but that requires credentials to be embedded in the uri. This is not ideal.
- Probably need some git provider auth class. Not a big deal just wanted to capture that somewhere.

## Notes

Customer is responsible for Git repo, could they do anything malicious with pre-commit hooks?

- No because hook aren't ran automatically

There's a lot of code related to Comments but we're not using it right now.
The hope was to leverage pr comments but we can't specify an actor for the comment.

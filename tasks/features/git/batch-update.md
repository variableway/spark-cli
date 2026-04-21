# Batch Update
Batch update is a feature that allows users to update multiple github repo folder in one command

## Task 1: Implement batch update command

1. create a subcommand for git to commit, and push all the repos in current folder to github
2. Use Case:
    1. in Current Folder, there are several github repos
    2. Some changes in these folders
    3. use spark git push-all to push all changes in git repo to github

verification:
1. in ../innate folder
2. using spark git push-all to push all changes in to github
3. if the current repo is not a github repo, ignore the push action, then go to next
4. if conflict occurs, then prompt user to resolve the conflict, and continue other repo's push action

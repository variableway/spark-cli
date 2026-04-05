# Git Commands

## Task 1: Create a Command for config current github user

1. Create a Command for a configured git user in current folder
2. git username and git email is configured in configuration file by default,
   and it will be used when commit code and push code.
3. could pass username and email as parameter to change git username and git email in current folder 
4. before change the username and email,show the current user and email in current folder first


## Task 2: create A Command to get current repo git url

1. ```cat .git/config | grep url``` can get the url 
2. but content include `url =` , so need to replace all the `url =` with empty string
3. create a command for this operation in git subcommand 

## Task 3: Create A command to git clone all the repos

1. given an org github account, try to git clone all the repos in this org
2. for example: https://github.com/variableway, then run the command to git clone all the repos in current folder
3. Create An command for this operation in git subcommand 
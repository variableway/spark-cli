# Agent Task

## Bug Fix

fix bug when run command ```spark agent use GLM```

```
spark agent use GLM
panic: unable to redefine 'p' shorthand in "use" flagset: it's already used for "project" flag

goroutine 1 [running]:
github.com/spf13/pflag.(*FlagSet).AddFlag(0x140001b8a00, 0x140001bcbe0)
	/Users/patrick/go/pkg/mod/github.com/spf13/pflag@v1.0.10/flag.go:904 +0x338
github.com/spf13/cobra.(*Command).mergePersistentFlags.(*FlagSet).AddFlagSet.func2(0x140001bcbe0)
	/Users/patrick/go/pkg/mod/github.com/spf13/pflag@v1.0.10/flag.go:917 +0x40
github.com/spf13/pflag.(*FlagSet).VisitAll(0x104cbd880?, 0x14000037af8)
	/Users/patrick/go/pkg/mod/github.com/spf13/pflag@v1.0.10/flag.go:320 +0xcc
github.com/spf13/pflag.(*FlagSet).AddFlagSet(...)
	/Users/patrick/go/pkg/mod/github.com/spf13/pflag@v1.0.10/flag.go:915
github.com/spf13/cobra.(*Command).mergePersistentFlags(0x104cbd880)å
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:1901 +0x7c
github.com/spf13/cobra.stripFlags({0x14000032ab0, 0x1, 0x1}, 0x104cbd880)
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:678 +0x3c
github.com/spf13/cobra.(*Command).Find.func1(0x104cbd880, {0x14000032ab0, 0x1, 0x1})
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:761 +0x48
github.com/spf13/cobra.(*Command).Find.func1(0x104cbbbc0, {0x140000770c0, 0x2, 0x2})
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:769 +0xa4
github.com/spf13/cobra.(*Command).Find.func1(0x104cbde40, {0x1400001e090, 0x3, 0x3})
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:769 +0xa4
github.com/spf13/cobra.(*Command).Find(0x104cbde40?, {0x1400001e090?, 0x1?, 0x2?})
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:774 +0x3c
github.com/spf13/cobra.(*Command).initCompleteCmd(0x104cbde40, {0x1400001e090, 0x3, 0x3})
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/completions.go:297 +0x1e8
github.com/spf13/cobra.(*Command).ExecuteC(0x104cbde40)
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:1110 +0x154
github.com/spf13/cobra.(*Command).Execute(...)
	/Users/patrick/go/pkg/mod/github.com/spf13/cobra@v1.10.2/command.go:1071
spark/cmd.Execute()
	/Users/patrick/innate/spark-cli/cmd/root.go:29 +0x24
main.main()
	/Users/patrick/innate/spark-cli/main.go:8 +0x1c
```

After fix to verify:
- run command ```spark agent use GLM```
- ~/.claude/setting.json file is exsiting only to set the api key
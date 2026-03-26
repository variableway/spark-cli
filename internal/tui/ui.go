package tui

import (
	"github.com/pterm/pterm"
)

type UI struct {
	useTUI bool
}

func New(useTUI bool) *UI {
	return &UI{useTUI: useTUI}
}

func (u *UI) Info(msg string) {
	if u.useTUI {
		pterm.Info.Println(msg)
	} else {
		pterm.DefaultBasicText.Println(msg)
	}
}

func (u *UI) Success(msg string) {
	pterm.Success.Println(msg)
}

func (u *UI) Error(msg string) {
	pterm.Error.Println(msg)
}

func (u *UI) Warning(msg string) {
	pterm.Warning.Println(msg)
}

func (u *UI) Printf(format string, args ...interface{}) {
	pterm.Printf(format, args...)
}

func (u *UI) Println(msg string) {
	pterm.Println(msg)
}

func (u *UI) Spinner(message string, action func() error) error {
	if u.useTUI {
		spinner, _ := pterm.DefaultSpinner.Start(message)
		err := action()
		if err != nil {
			spinner.Fail(message + ": " + err.Error())
			return err
		}
		spinner.Success(message)
		return nil
	}
	pterm.Println(message + "...")
	return action()
}

func (u *UI) Header(title string) {
	pterm.DefaultHeader.WithFullWidth().Println(title)
}

func (u *UI) Table(headers []string, rows [][]string) {
	table := pterm.DefaultTable.WithHasHeader()
	tableData := pterm.TableData{headers}
	tableData = append(tableData, rows...)
	table.WithData(tableData).Render()
}

func (u *UI) Section(title string) {
	pterm.DefaultSection.Println(title)
}

func (u *UI) BulletList(items []string) {
	var listItems []pterm.BulletListItem
	for _, item := range items {
		listItems = append(listItems, pterm.BulletListItem{Level: 0, Text: item})
	}
	pterm.DefaultBulletList.WithItems(listItems).Render()
}

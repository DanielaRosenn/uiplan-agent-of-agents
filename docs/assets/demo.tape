# VHS tape for the UiPath Claude Code hero demo.
# Render with: vhs docs/assets/demo.tape
# Produces: docs/assets/demo.gif
#
# Prerequisites on the recording machine:
#   - vhs (https://github.com/charmbracelet/vhs)
#   - UiPath Claude Code installed (`pip install -e ".[dev]"`)
#   - AWS Bedrock creds valid (`aws sts get-caller-identity`)
#   - UiPath Studio Desktop 26.2+ running
#   - $env:UIPATH_AGENTIC_MODE = "1"
#
# Target length: ~30 seconds.

Output docs/assets/demo.gif

Set Shell "pwsh"
Set FontSize 14
Set Width 1100
Set Height 620
Set Padding 20
Set Theme "Catppuccin Mocha"

Type "uipath-claude chat" Sleep 400ms Enter
Sleep 2s

Type "Build me an InvoiceProcessor workflow that reads Sample.xlsx and logs each invoice id."
Sleep 600ms Enter
Sleep 20s

Type "exit" Sleep 200ms Enter
Sleep 1s

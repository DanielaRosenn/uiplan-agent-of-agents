# UiPath Builder Agent - User Guide

**Welcome to the UiPath Builder Agent!** This guide will help you get started building UiPath RPA projects using AI-powered automation.

---

## Table of Contents

1. [What is UiPath Builder Agent?](#what-is-uipath-builder-agent)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Getting Started](#getting-started)
6. [Using Bootstrap Mode](#using-bootstrap-mode)
7. [Using Conversational Mode](#using-conversational-mode)
8. [Understanding the Workflow](#understanding-the-workflow)
9. [Common Use Cases](#common-use-cases)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)

---

## What is UiPath Builder Agent?

The UiPath Builder Agent is an AI-powered tool that helps you create UiPath RPA (Robotic Process Automation) projects through natural conversation. Instead of manually creating workflows, you describe what you want to automate, and the agent generates the complete project structure with proper code and configuration.

### Key Features

✅ **Conversational Interface** - Describe your automation in plain English  
✅ **Automatic Code Generation** - Generates C# coded workflows  
✅ **Best Practices Built-In** - Enforces UiPath standards and constraints  
✅ **Quality Validation** - Automatically checks generated code  
✅ **Human-in-the-Loop** - Reviews complex designs before generation  
✅ **Dynamic Skills** - Accesses specialized UiPath knowledge

### What Can It Build?

- **Dispatcher/Performer** patterns for queue-based processing
- **Linear Workflows** for sequential automation tasks
- **Custom Activities** with proper error handling
- **Configuration Management** with Config.xlsx
- **Exception Handling** following UiPath best practices

---

## Prerequisites

### System Requirements

- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Version 3.11 or higher
- **Git:** For cloning the repository
- **Internet Connection:** Required for AWS Bedrock API calls

### Required Accounts

1. **AWS Account** with access to Amazon Bedrock
   - Claude Sonnet 4.5 model enabled
   - Proper IAM permissions configured

### Optional (Recommended)

- **UiPath Studio:** To open and test generated projects
- **Code Editor:** VS Code or similar for viewing generated code

---

## Installation

### Step 1: Clone the Repository

```bash
cd /c/Users/YourUsername/projects
git clone https://github.com/your-org/uipath-builder-agent.git
cd uipath-builder-agent-sprint-1
```

### Step 2: Initialize Git Submodules

The agent uses UiPath skills from a separate repository:

```bash
git submodule update --init --recursive
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows Git Bash)
source venv/Scripts/activate

# Activate it (Windows Command Prompt)
venv\Scripts\activate.bat

# Activate it (macOS/Linux)
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -e .
```

This installs:
- LangGraph (for orchestration)
- LangChain AWS (for Claude integration)
- Typer (for CLI)
- PyYAML (for configuration)
- All testing tools (pytest, ruff, mypy, black)

### Step 5: Verify Installation

```bash
# Check that installation worked
python -m cli.main --help

# You should see:
# Usage: cli.main [OPTIONS] COMMAND [ARGS]...
#   UiPath Builder Agent - AI-powered RPA project generator
# Commands:
#   chat           Start conversational mode
#   start-project  Start the bootstrap flow
```

---

## Configuration

### Step 1: Set Up AWS Credentials

The agent uses AWS Bedrock to access Claude AI. You need to configure your AWS credentials.

#### Option A: AWS CLI Configuration (Recommended)

```bash
# Install AWS CLI if not already installed
# Download from: https://aws.amazon.com/cli/

# Configure credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-1
# Default output format: json
```

#### Option B: Environment Variables

```bash
# Create .env file in project root
cat > .env << EOF
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
EOF
```

#### Option C: AWS Profile

```bash
# If you have multiple AWS profiles
export AWS_PROFILE=your-profile-name

# Or add to .env file
echo "AWS_PROFILE=your-profile-name" >> .env
```

### Step 2: Verify AWS Connection

```bash
# Test AWS Bedrock access
aws bedrock list-foundation-models --region us-east-1 | grep claude-sonnet

# You should see Claude models listed
```

### Step 3: Configure Agent Settings (Optional)

Create or edit `.env` file for custom settings:

```bash
# .env file
AWS_REGION=us-east-1
AWS_PROFILE=default

# Optional: Override default model
LLM_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# Optional: Set output directory
OUTPUT_DIR=./generated-projects
```

---

## Getting Started

### Your First Project

Let's create your first UiPath automation project!

#### 1. Activate Virtual Environment

```bash
cd /c/Users/YourUsername/projects/uipath-builder-agent-sprint-1
source venv/Scripts/activate
```

#### 2. Start Bootstrap Mode

```bash
python -m cli.main start-project
```

You'll see:

```
============================================================
  UiPath Builder Agent - Bootstrap Flow
============================================================

Describe the process you want to automate:
```

#### 3. Describe Your Automation

Be specific! The more details you provide, the better the result.

**Example 1 - Simple Invoice Processing:**
```
I need to automate invoice processing. The robot should:
1. Read invoices from a folder
2. Extract invoice number, date, and amount using OCR
3. Validate the data
4. Update the amounts in an Excel spreadsheet
5. Move processed invoices to an archive folder
6. Send an email summary when done
```

**Example 2 - Data Entry Automation:**
```
Automate data entry from Excel to a web application. The process should:
1. Read employee data from Excel (Name, Department, Salary)
2. Log into the HR portal
3. Navigate to the employee registration page
4. Fill in the form for each employee
5. Save and verify each entry
6. Log any errors to a separate sheet
```

#### 4. Wait for Analysis

The agent will analyze your request:

```
[BA] Analyzing requirements...
[SA] Creating technical design...
```

#### 5. Review the Design (If Needed)

For complex projects, you'll see a design review:

```
====================================================================
  HUMAN REVIEW REQUIRED
====================================================================

The Solution Architect has produced a design. Please review before
code generation begins.

---- PROJECT ---------------------------------------------------
  Name       : InvoiceProcessor
  Namespace  : Company.InvoiceProcessor
  Template   : linear-workflow
  Complexity : moderate

---- CODED ACTIVITIES TO GENERATE ------------------------------
  - ReadInvoices: Read PDF invoices from input folder
  - ExtractData: Extract invoice data using OCR
  - ValidateData: Validate extracted data
  - UpdateExcel: Update Excel with validated data
  - ArchiveInvoices: Move processed invoices to archive

Options:
  - "approved"           -> proceed with this design
  - "rejected: reason"   -> abort generation
----------------------------------------------------------------

Your review: 
```

Type `approved` to continue or `rejected: reason` to stop.

#### 6. Get Generated Files

After approval, the agent generates your project:

```
Generated 6 files for InvoiceProcessor:
  - project.json
  - Main.cs
  - ReadInvoices.cs
  - ExtractData.cs
  - ValidateData.cs
  - UpdateExcel.cs
  - ArchiveInvoices.cs

Files saved to: ./output/InvoiceProcessor/
```

#### 7. Open in UiPath Studio

```bash
# Navigate to output folder
cd ./output/InvoiceProcessor

# Open project.json in UiPath Studio
# File > Open > Select project.json
```

---

## Using Bootstrap Mode

Bootstrap mode is perfect for creating new projects from scratch. It guides you through a structured workflow.

### The Bootstrap Workflow

```
1. BA (Business Analyst)
   └─> Gathers requirements, asks clarifying questions

2. SA (Solution Architect)
   └─> Creates technical design (SDD)

3. HITL (Human-in-the-Loop)
   └─> You review and approve the design

4. Developer
   └─> Generates C# coded workflows

5. QA (Quality Assurance)
   └─> Validates against UiPath constraints

6. Done!
   └─> Your project is ready
```

### Command Options

```bash
# With description provided
python -m cli.main start-project -d "Automate invoice processing"

# With custom output directory
python -m cli.main start-project -o ./my-projects

# Both options
python -m cli.main start-project \
  -d "Process customer orders" \
  -o ./projects/order-automation
```

### What Gets Generated

Every project includes:

1. **project.json** - UiPath project configuration
   - Project name and description
   - NuGet package dependencies
   - Target framework (Windows)
   - Expression language (C#)
   - Entry points

2. **Main.cs** - Entry point coded workflow
   - Calls all activities in sequence
   - Proper logging
   - Error handling structure

3. **Activity Files** - One .cs file per activity
   - Each activity is a separate coded workflow
   - Input/output parameters
   - Logging statements
   - TODO comments for implementation

---

## Using Conversational Mode

Conversational mode is for free-form interaction, asking questions, and iterative development.

### Starting Conversational Mode

```bash
python -m cli.main chat
```

You'll see:

```
============================================================
  UiPath Builder Agent - Conversational Mode
============================================================
  Type 'exit' or 'quit' to end the session
============================================================

You: 
```

### What You Can Do

#### Ask Questions

```
You: What are the best practices for exception handling in UiPath?

Agent: Here are the key best practices for exception handling:

1. Use BusinessRuleException for expected errors
2. Use ApplicationException for unexpected errors
3. Always log exceptions with proper severity
4. Implement retry logic with exponential backoff
5. ...
```

#### Request Code Snippets

```
You: Show me how to read an Excel file with error handling

Agent: Here's a coded workflow example:
[Provides C# code example]
```

#### Get Skill Information

```
You: What skills are available?

Agent: Available UiPath skills:
- uipath-rpa-workflows: Create visual XAML workflows
- uipath-coded-workflows: Generate C# coded activities
- uipath-orchestrator: Orchestrator integration
...
```

#### Invoke Skills Directly

```
You: Use the rpa-workflows skill to generate a Main.xaml for invoice processing

Agent: [Invokes skill and returns generated XAML]
```

### Exiting Conversational Mode

Type any of these:
- `exit`
- `quit`
- `q`

Or press `Ctrl+C`

---

## Understanding the Workflow

### The HARD_CONSTRAINTS

Every generated project automatically enforces these UiPath standards:

✅ **C# Only** - No VB.Net code (modern standard)  
✅ **Modern Activities** - Uses latest UiPath activities  
✅ **Windows Target** - Configured for Windows execution  
✅ **LogMessage** - Proper logging (no Console.Write)  
✅ **Config.xlsx** - Configuration in Excel (no hardcoding)  
✅ **No Secrets** - No passwords or API keys in code  
✅ **Proper Exceptions** - BusinessRuleException vs ApplicationException  
✅ **Modern Namespaces** - Latest UiPath namespace conventions

If QA validation fails, the Developer node will retry (up to 2 attempts).

### Project Templates

The agent supports three UiPath architecture patterns:

#### 1. Dispatcher/Performer (Queue-Based)

**Use When:** Processing many items from a queue

**Example:** Processing 1000 invoices
- Dispatcher: Adds invoices to queue
- Performer: Processes each queue item

**Generated Structure:**
```
Dispatcher.cs   - Reads data, adds to queue
Performer.cs    - Processes queue items
Main.cs        - Orchestrates both
```

#### 2. Linear Workflow (Sequential)

**Use When:** Simple step-by-step process

**Example:** Daily report generation
- Read data
- Process data
- Generate report
- Send email

**Generated Structure:**
```
Main.cs                - Entry point
ReadData.cs           - Activity 1
ProcessData.cs        - Activity 2
GenerateReport.cs     - Activity 3
SendEmail.cs          - Activity 4
```

#### 3. REFramework (Robust Enterprise)

**Use When:** Complex enterprise automation with proper error handling

**Example:** Mission-critical financial processing

**Generated Structure:**
```
Main.cs               - State machine entry
Initialization.cs     - Setup
GetTransactionData.cs - Get next item
ProcessTransaction.cs - Process item
EndProcess.cs         - Cleanup
```

---

## Common Use Cases

### Use Case 1: Invoice Processing Automation

**Scenario:** Your company receives 100+ invoices daily via email. You need to extract data and update the accounting system.

**Steps:**

1. Start bootstrap mode:
```bash
python -m cli.main start-project
```

2. Describe the process:
```
Automate invoice processing:
1. Download invoices from email inbox
2. Extract vendor name, invoice number, date, and amount
3. Validate invoice data against business rules
4. Update SAP with invoice details
5. Move processed invoices to archive
6. Send exception report for failed invoices
```

3. Review generated design (approve it)

4. Open generated project in UiPath Studio

5. Implement TODOs:
   - Add email credentials to Config.xlsx
   - Configure SAP connection details
   - Implement OCR for invoice extraction
   - Add business validation rules

6. Test and deploy!

### Use Case 2: Employee Onboarding

**Scenario:** Automate new employee setup across multiple systems.

**Steps:**

1. Start bootstrap mode with description:
```bash
python -m cli.main start-project -d "Employee onboarding automation:
Read new employee data from Excel.
Create user accounts in Active Directory.
Set up email in Exchange.
Register in HR system.
Generate welcome email with credentials.
Log all actions for audit trail."
```

2. Review and approve design

3. Implement system-specific TODOs:
   - AD credentials in Config.xlsx
   - Exchange connection settings
   - HR system API details

### Use Case 3: Report Generation

**Scenario:** Daily sales report sent to management.

**Conversational approach:**

```bash
python -m cli.main chat
```

```
You: I need to create a daily sales report automation

Agent: I can help! Let me understand your requirements:
- Where does the sales data come from?
- What format should the report be in?
- Who should receive it?

You: Sales data is in SQL database. Report should be Excel with charts. 
     Send to sales manager and CEO via email.

Agent: Great! For this use case, I recommend:
1. QuerySalesData activity - SQL query
2. GenerateExcelReport activity - Excel creation
3. CreateCharts activity - Charts and formatting
4. SendReportEmail activity - Email distribution

Would you like me to generate this project?

You: Yes, generate it

Agent: [Switches to bootstrap mode internally and generates project]
```

### Use Case 4: Data Migration

**Scenario:** Migrate 10,000 customer records from legacy system to new CRM.

**Approach: Dispatcher/Performer**

```bash
python -m cli.main start-project -d "Data migration automation:
Dispatcher:
- Read customer records from legacy database
- Add each record to Orchestrator queue
Performer:
- Get customer from queue
- Transform data to new format
- Insert into new CRM
- Mark as complete or failed with reason"
```

---

## Tips & Best Practices

### Getting Better Results

#### ✅ DO: Be Specific

**Good:**
```
Create an invoice processing automation that:
1. Reads PDF invoices from C:\Invoices\Input
2. Extracts vendor name, invoice number, date, and total amount
3. Validates that amount is less than $10,000
4. Updates Excel file at C:\Invoices\Tracker.xlsx
5. Moves processed files to C:\Invoices\Archive
```

**Bad:**
```
Process invoices
```

#### ✅ DO: Mention Error Scenarios

**Good:**
```
If invoice extraction fails, move to C:\Invoices\Failed and log error.
If amount exceeds $10,000, send alert email to supervisor.
Retry failed items up to 3 times.
```

**Bad:**
```
Just process the invoices
```

#### ✅ DO: Include Business Rules

**Good:**
```
Validation rules:
- Invoice date must be within last 90 days
- Vendor must exist in approved vendors list
- Amount must match PO amount within 5%
- Invoice number must be unique
```

**Bad:**
```
Validate the data
```

#### ✅ DO: Specify Data Sources

**Good:**
```
Read employee data from:
- Excel file: C:\HR\NewEmployees.xlsx
- Columns: FirstName, LastName, Department, StartDate, Salary
```

**Bad:**
```
Get employee data from Excel
```

### Configuration Best Practices

1. **Store Credentials Securely**
   - Use Config.xlsx for non-sensitive config
   - Use Windows Credential Manager for passwords
   - Use Orchestrator Assets for production

2. **Use Descriptive Names**
   - Project: "InvoiceProcessing" not "Project1"
   - Activities: "ExtractInvoiceData" not "Activity1"

3. **Follow UiPath Naming Conventions**
   - PascalCase for activities: `ProcessTransaction`
   - camelCase for variables: `invoiceNumber`
   - UPPER_CASE for constants: `MAX_RETRIES`

4. **Implement Logging**
   - Log entry to each activity
   - Log important data values
   - Log exceptions with stack traces

### Testing Your Generated Projects

1. **Unit Test Each Activity**
   ```
   Test ReadInvoices:
   - Place 1 test invoice in input folder
   - Run activity
   - Verify invoice is read correctly
   ```

2. **Test Error Scenarios**
   ```
   Test ExtractData with corrupted PDF:
   - Verify error is caught
   - Verify error is logged
   - Verify file moves to failed folder
   ```

3. **Test End-to-End**
   ```
   Run complete workflow with 10 test invoices:
   - 8 valid invoices
   - 1 corrupted file
   - 1 duplicate invoice
   Verify all scenarios handled correctly
   ```

---

## Troubleshooting

### Common Issues

#### Issue 1: AWS Authentication Failed

**Error:**
```
Error: Unable to locate credentials
```

**Solution:**
```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

**Verify:**
```bash
aws sts get-caller-identity
```

#### Issue 2: Claude Model Not Accessible

**Error:**
```
Error: Could not access model us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Solution:**
1. Check model is enabled in AWS Bedrock console
2. Verify region is correct (us-east-1)
3. Check IAM permissions include `bedrock:InvokeModel`

**Verify:**
```bash
aws bedrock list-foundation-models --region us-east-1 | grep claude
```

#### Issue 3: Skills Not Found

**Error:**
```
Warning: No skills found in skills directory
```

**Solution:**
```bash
# Initialize git submodules
git submodule update --init --recursive

# Verify skills exist
ls skills/
```

#### Issue 4: Tests Failing

**Error:**
```
pytest: 1 failed, 52 passed
```

**Solution:**
```bash
# Run with verbose output to see which test failed
pytest -v --tb=short

# Run specific failing test
pytest tests/unit/test_bootstrap_flow.py::test_name -v

# Check test requirements
pip install -e .
```

#### Issue 5: Generated Project Won't Open in UiPath Studio

**Error:**
```
Invalid project.json format
```

**Solution:**
1. Check project.json is valid JSON:
   ```bash
   cat output/YourProject/project.json | python -m json.tool
   ```

2. Verify project.json has required fields:
   - `name`
   - `main`
   - `expressionLanguage: "CSharp"`
   - `targetFramework: "Windows"`

3. Regenerate if needed:
   ```bash
   python -m cli.main start-project -d "Your description"
   ```

### Getting Help

#### Check Logs

```bash
# Run with verbose output
python -m cli.main start-project -d "Your description" --verbose

# Check recent errors
grep ERROR *.log
```

#### Run Diagnostics

```bash
# Verify installation
python -m cli.main --help

# Verify AWS connection
aws bedrock list-foundation-models --region us-east-1

# Verify Python version
python --version  # Should be 3.11+

# Verify dependencies
pip list | grep -E "langgraph|langchain"
```

#### Community Support

- **GitHub Issues:** https://github.com/your-org/uipath-builder-agent/issues
- **Email Support:** support@your-org.com
- **Documentation:** This guide and API_DOCUMENTATION.md

---

## FAQ

### General Questions

**Q: Do I need UiPath Studio to use this?**

A: No, you can generate projects without UiPath Studio. However, you'll need Studio to run and test the generated projects.

**Q: Can I edit the generated code?**

A: Yes! The generated code is fully editable. Think of it as a starting point that follows best practices. Add your business logic where you see TODO comments.

**Q: Does this work with UiPath Cloud?**

A: Yes! Generated projects work with both UiPath Studio (desktop) and UiPath Cloud (browser-based).

**Q: How much does it cost to use?**

A: The agent itself is open source. You'll need an AWS account with Bedrock access (pay per API call). Typical project generation costs $0.10-$0.50 in API calls.

### Technical Questions

**Q: Which UiPath version is supported?**

A: Generated projects target UiPath Studio 2024.10+ with modern activities. Projects use C# coded workflows (not legacy XAML).

**Q: Can I generate XAML workflows?**

A: Currently the agent generates C# coded workflows by default. XAML support is available through the conversational mode by invoking the `uipath-rpa-workflows` skill.

**Q: Is my data sent to the cloud?**

A: Your automation descriptions are sent to AWS Bedrock (Claude AI) for processing. No code or data is stored permanently. Review AWS Bedrock privacy policy for details.

**Q: Can I use this offline?**

A: No, the agent requires internet connection to access Claude AI via AWS Bedrock.

**Q: How do I update the agent?**

A: 
```bash
cd uipath-builder-agent-sprint-1
git pull origin main
git submodule update --recursive
pip install -e .
```

### Workflow Questions

**Q: Can I modify the design after approval?**

A: Not in the current session. If you want changes, reject the design and provide feedback. The agent will regenerate with your input.

**Q: How long does generation take?**

A: Typically 30-60 seconds for a complete project with 5-10 activities.

**Q: Can I generate multiple projects in one session?**

A: Yes! In conversational mode, you can generate multiple projects. Each call to `start-project` creates a new project.

**Q: What if the generated code doesn't work?**

A: The agent generates syntactically correct code structure and enforces UiPath constraints. You'll need to implement business-specific logic in the TODO sections. Test thoroughly!

### Advanced Questions

**Q: Can I add my own skills?**

A: Yes! Skills are in the `skills/` directory. See CONTRIBUTING.md for instructions on creating custom skills.

**Q: Can I customize the prompts?**

A: Yes, prompts are in `agent/nodes/` files. Edit the system prompts to customize agent behavior.

**Q: Can I integrate this into my CI/CD?**

A: Yes! The CLI can be scripted:
```bash
python -m cli.main start-project -d "$(cat requirements.txt)" -o ./output
```

**Q: Can I use a different LLM?**

A: The code uses AWS Bedrock with Claude. To use other LLMs, you'd need to modify `agent/nodes/*.py` files to use different model providers.

---

## Next Steps

Now that you've learned the basics:

1. **Try Bootstrap Mode**
   - Generate a simple project
   - Open in UiPath Studio
   - Implement one activity
   - Run and test

2. **Explore Conversational Mode**
   - Ask questions about UiPath
   - Request code examples
   - Learn about available skills

3. **Read API Documentation**
   - See `docs/API_DOCUMENTATION.md`
   - Understand the architecture
   - Learn about customization

4. **Join the Community**
   - Share your projects
   - Report issues
   - Contribute improvements

---

## Quick Reference Card

### Bootstrap Mode Commands

```bash
# Interactive
python -m cli.main start-project

# With description
python -m cli.main start-project -d "Description here"

# Custom output
python -m cli.main start-project -o ./my-output
```

### Conversational Mode Commands

```bash
# Start chat
python -m cli.main chat

# In chat:
You: What skills are available?
You: Show me exception handling example
You: Use rpa-workflows skill to generate Main.xaml
You: exit
```

### File Locations

```
./output/ProjectName/          - Generated projects
./skills/                       - UiPath skills
./.env                          - Configuration
./tests/                        - Test suites
./docs/                         - Documentation
```

### Key Commands

```bash
# Installation
pip install -e .

# Tests
pytest
pytest --cov=agent --cov=cli

# Code quality
ruff check agent cli
mypy agent cli --ignore-missing-imports
black agent cli

# AWS verify
aws bedrock list-foundation-models --region us-east-1
```

---

## Appendix: Example Projects

### Example 1: Complete Invoice Processing

**Input Description:**
```
Create an invoice processing automation:

1. Read PDF invoices from C:\Invoices\Input
2. Extract data using OCR:
   - Vendor name
   - Invoice number
   - Invoice date
   - Total amount
3. Validate data:
   - Invoice date within last 90 days
   - Amount less than $50,000
   - No duplicate invoice numbers
4. Update Excel tracker: C:\Invoices\Tracker.xlsx
5. Move processed to: C:\Invoices\Processed
6. Move failed to: C:\Invoices\Failed
7. Send daily summary email to accounting@company.com
```

**Generated Structure:**
```
InvoiceProcessor/
├── project.json
├── Main.cs
├── ReadInvoices.cs
├── ExtractInvoiceData.cs
├── ValidateInvoice.cs
├── UpdateTracker.cs
├── MoveInvoiceToArchive.cs
└── SendSummaryEmail.cs
```

### Example 2: Employee Onboarding

**Input Description:**
```
Automate employee onboarding:

1. Read new employee Excel: C:\HR\NewHires.xlsx
   Columns: FirstName, LastName, Department, StartDate, Email
2. Create AD account with username: firstname.lastname
3. Add to department security group in AD
4. Create Office 365 mailbox
5. Send welcome email with credentials
6. Update HR system via API
7. Log all actions to C:\HR\Logs\onboarding.log
```

**Generated Structure:**
```
EmployeeOnboarding/
├── project.json
├── Main.cs
├── ReadNewEmployees.cs
├── CreateADAccount.cs
├── AssignSecurityGroup.cs
├── CreateO365Mailbox.cs
├── SendWelcomeEmail.cs
└── UpdateHRSystem.cs
```

---

**End of User Guide**

Need help? Email: support@your-org.com | Documentation: https://github.com/your-org/uipath-builder-agent

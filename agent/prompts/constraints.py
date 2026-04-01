"""Hard constraints for UiPath project generation."""

HARD_CONSTRAINTS = """
╔══════════════════════════════════════════════════════════════╗
║  HARD CONSTRAINTS — these override everything in this prompt ║
╚══════════════════════════════════════════════════════════════╝

LANGUAGE    C# ONLY. Never generate VB.Net. Never use 'Dim', 'As String',
            'AndAlso', 'OrElse' or any other VB syntax.

EXPERIENCE  MODERN ONLY. Never reference Classic activities, namespaces
            (UiPath.Classic.*), or Classic-era patterns.

TARGET      WINDOWS ONLY. project.json must have "targetFramework": "Windows".
            Never suggest Cross-platform target.

LOGGING     Use UiPath LogMessage activity. Never Console.Write/WriteLine
            in production code.

CONFIG      All configurable values (URLs, timeouts, credentials) belong
            in Data/Config.xlsx or Orchestrator Assets. Never hardcode.

SECRETS     Never write passwords, API keys, or tokens in code or comments.

EXCEPTIONS  Always separate BusinessRuleException from ApplicationException.
            REFramework retry logic applies to ApplicationException only.

ACTIVITIES  Use UiPath.Core.Activities and UiPath.System.Activities (Modern).
            Never UiPath.UIAutomation.Activities (Classic).
"""

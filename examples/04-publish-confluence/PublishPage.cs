// Coded workflow: publish UiPath Claude Code docs to the Cato RPA Confluence space
// via the UiPath Integration Service Atlassian Confluence connector.
//
// Pattern reference:
//   skills/skills/uipath-rpa/references/coded/integration-service-guide.md
//
// Required UiPath.IntegrationService.Activities package is pinned in project.json.
// The AtlassianConfluence connection handle is expected to be generated into
// ISConnections.cs by Studio when the Integration Service connection is added
// to this project. See the example's README for the one-time connection setup.

using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using UiPath.CodedWorkflows;
using UiPath.IntegrationService.Activities.Runtime.CodedWorkflows;
using UiPath.IntegrationService.Activities.Runtime.Models;
using UiPath.IntegrationService.Activities.Runtime.Models.ConnectorMetadata;

namespace PublishConfluence
{
    public class PublishPage : CodedWorkflow
    {
        // Both pages live directly under the RPA space home unless a
        // CONFLUENCE_PARENT_PAGE_ID env var overrides the parent.
        private const string SpaceKeyEnv = "CONFLUENCE_SPACE_KEY";
        private const string ParentIdEnv = "CONFLUENCE_PARENT_PAGE_ID";
        private const string IdMapFile = "..\\..\\docs\\wiki\\.confluence-ids.json";

        [Workflow]
        public async Task Execute(string overviewPath, string quickstartPath)
        {
            var spaceKey = Environment.GetEnvironmentVariable(SpaceKeyEnv) ?? "RPA";
            var parentId = Environment.GetEnvironmentVariable(ParentIdEnv);

            var ids = LoadIdMap(IdMapFile);

            ids["overview"] = await UpsertPageAsync(
                title: "UiPath Claude Code - Overview",
                markdownPath: overviewPath,
                spaceKey: spaceKey,
                parentId: parentId,
                existingId: ids.TryGetValue("overview", out var oid) ? oid : null);

            ids["quickstart"] = await UpsertPageAsync(
                title: "UiPath Claude Code - Quickstart for developers",
                markdownPath: quickstartPath,
                spaceKey: spaceKey,
                parentId: parentId,
                existingId: ids.TryGetValue("quickstart", out var qid) ? qid : null);

            SaveIdMap(IdMapFile, ids);
            Log($"Published {ids.Count} pages. IDs: overview={ids["overview"]}, quickstart={ids["quickstart"]}");
        }

        private async Task<string> UpsertPageAsync(
            string title,
            string markdownPath,
            string spaceKey,
            string? parentId,
            string? existingId)
        {
            var markdown = File.ReadAllText(markdownPath);
            var storageFormat = MarkdownToConfluenceStorage(markdown);

            var connection = ISConnections.AtlassianConfluence;
            var isCreate = string.IsNullOrEmpty(existingId);

            var config = new CodedConnectorConfiguration(
                connection: connection,
                objectName: "pages",
                operation: isCreate ? Operation.Create : Operation.Update,
                httpMethod: isCreate ? "POST" : "PUT",
                path: isCreate ? "/wiki/api/v2/pages" : "/wiki/api/v2/pages/{id}");

            var body = new Dictionary<string, object?>
            {
                ["spaceId"] = spaceKey,
                ["title"] = title,
                ["body"] = new Dictionary<string, object?>
                {
                    ["representation"] = "storage",
                    ["value"] = storageFormat,
                },
            };
            if (!isCreate)
            {
                body["id"] = existingId;
                body["version"] = new Dictionary<string, object?> { ["number"] = DateTime.UtcNow.Ticks };
            }
            if (!string.IsNullOrEmpty(parentId))
            {
                body["parentId"] = parentId;
            }

            var request = new ConnectorRequest
            {
                PathParameters = isCreate
                    ? new Dictionary<string, string>()
                    : new Dictionary<string, string> { ["id"] = existingId! },
                BodyParameters = body,
            };

            var response = await ConnectorConnection.ExecuteAsync(config, request);
            if (!response.IsSuccess)
            {
                throw new InvalidOperationException(
                    $"Confluence {(isCreate ? "create" : "update")} failed for '{title}': {response.StatusCode} {response.ErrorMessage}");
            }

            using var doc = JsonDocument.Parse(response.Body ?? "{}");
            var newId = doc.RootElement.TryGetProperty("id", out var idProp) ? idProp.GetString() : existingId;
            return newId ?? throw new InvalidOperationException("Confluence response did not include a page id.");
        }

        // Minimal Markdown -> Confluence storage-format converter.
        // Handles headings, paragraphs, fenced code blocks, and inline code.
        // Swap in a fuller renderer (e.g. md2cf) if richer Markdown is needed.
        private static string MarkdownToConfluenceStorage(string markdown)
        {
            var lines = markdown.Replace("\r\n", "\n").Split('\n');
            var sb = new System.Text.StringBuilder();
            bool inCode = false;
            foreach (var raw in lines)
            {
                var line = raw;
                if (line.StartsWith("```"))
                {
                    if (inCode)
                    {
                        sb.AppendLine("</ac:plain-text-body></ac:structured-macro>");
                        inCode = false;
                    }
                    else
                    {
                        sb.AppendLine("<ac:structured-macro ac:name=\"code\"><ac:plain-text-body><![CDATA[");
                        inCode = true;
                    }
                    continue;
                }
                if (inCode)
                {
                    sb.AppendLine(line);
                    continue;
                }
                if (line.StartsWith("# "))
                {
                    sb.AppendLine($"<h1>{HtmlEncode(line.Substring(2))}</h1>");
                }
                else if (line.StartsWith("## "))
                {
                    sb.AppendLine($"<h2>{HtmlEncode(line.Substring(3))}</h2>");
                }
                else if (line.StartsWith("### "))
                {
                    sb.AppendLine($"<h3>{HtmlEncode(line.Substring(4))}</h3>");
                }
                else if (string.IsNullOrWhiteSpace(line))
                {
                    sb.AppendLine();
                }
                else
                {
                    sb.AppendLine($"<p>{HtmlEncode(line)}</p>");
                }
            }
            if (inCode)
            {
                sb.AppendLine("]]></ac:plain-text-body></ac:structured-macro>");
            }
            return sb.ToString();
        }

        private static string HtmlEncode(string s)
            => s.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

        private static Dictionary<string, string> LoadIdMap(string path)
        {
            if (!File.Exists(path))
            {
                return new Dictionary<string, string>();
            }
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<Dictionary<string, string>>(json)
                ?? new Dictionary<string, string>();
        }

        private static void SaveIdMap(string path, Dictionary<string, string> ids)
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }
            var json = JsonSerializer.Serialize(ids, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
        }
    }
}

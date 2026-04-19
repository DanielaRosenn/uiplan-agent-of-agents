# Common permission errors

| error | required role |
|---|---|
| Cannot create folder | Folder Administrator on parent |
| Cannot read asset | Assets View on the folder |
| Cannot run process | Jobs Create + Folder View |
| Cannot publish package | Automation Publisher on the tenant |
| Cannot read Data Fabric entity | Data Fabric Reader on the entity |

## Diagnosing

```bash
uip platform user roles --user <email>
uip platform folder permissions --folder <name>
```

The second command shows which roles each user/group has on the folder. Grant via Orchestrator UI or REST.

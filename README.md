# V68 NTE official candidate discovery

Upload the three code/workflow files at their exact paths to GitHub (overwrite update.yml). No calendar UI or events.json edits.

GitHub Actions > Update Game Events > Run workflow. Download artifact `nte-official-candidates-v68` and inspect report.json.

V68 detects up to five latest official update notices and extracts candidate text and nearby date evidence. **It does not auto-register candidates**: a nearby date is not proof of an event's precise start/end. The existing V67 verified Hunter Pass import continues unchanged. Network failures are recorded in the report, not silently treated as new events. For confirmed future events, a later patch can add exact verified dates safely.

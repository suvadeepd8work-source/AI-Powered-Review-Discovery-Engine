# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automating the review analysis pipeline.

## Weekly Pipeline Workflow

**File:** `.github/workflows/weekly-pipeline.yml`

### Overview

The weekly pipeline workflow automatically executes the complete review analysis pipeline every Monday at 10:00 AM IST (4:30 AM UTC). It performs the following steps:

1. **Checkout repository** - Retrieves the latest code
2. **Set up Python environment** - Configures Python 3.11 with pip caching
3. **Install dependencies** - Installs all required packages from requirements.txt files
4. **Create directories** - Sets up necessary output and log directories
5. **Execute pipeline** - Runs the scheduler in the specified mode
6. **Upload artifacts** - Stores pipeline results, reports, and logs
7. **Generate summary** - Creates a workflow execution summary
8. **Notify on failure** - Alerts if pipeline execution fails

### Schedule

- **Frequency:** Weekly (every Monday)
- **Time:** 10:00 AM IST (4:30 AM UTC)
- **Cron Expression:** `30 4 * * 1`

### Manual Execution

You can manually trigger the workflow from the GitHub Actions tab:

1. Navigate to **Actions** tab in your repository
2. Select **Weekly Review Analysis Pipeline** workflow
3. Click **Run workflow**
4. Choose execution mode:
   - `schedule` - Runs the scheduler (default)
   - `run-now` - Executes pipeline immediately
   - `status` - Checks scheduler status only

### Required Secrets

Configure the following secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for LLM processing | Yes |

### Artifacts

The workflow uploads the following artifacts:

| Artifact Name | Contents | Retention |
|---------------|----------|-----------|
| `pipeline-results` | JSON outputs, markdown reports, logs, database | 30 days |
| `executive-report` | Executive report (JSON and Markdown) | 90 days |
| `scheduler-logs` | Scheduler execution logs | 30 days |

### Environment Variables

The workflow uses the following environment variables:

- `GROQ_API_KEY`: Retrieved from GitHub Secrets
- `DB_CONN_STR`: SQLite database connection string (default: `sqlite:///pipeline_state.db`)

### Workflow Summary

After each execution, a summary is generated in the GitHub Actions UI showing:
- Execution time
- Trigger type (schedule or manual)
- Run mode
- Pipeline completion status
- Links to uploaded artifacts

### Troubleshooting

**Workflow fails with "GROQ_API_KEY not found":**
- Ensure the `GROQ_API_KEY` secret is configured in repository settings

**Pipeline execution fails:**
- Check the `scheduler-logs` artifact for detailed error messages
- Review the workflow summary for execution status

**Artifacts not uploaded:**
- Ensure the output directories exist before pipeline execution
- Check GitHub Actions storage limits

### Local Testing

To test the pipeline locally before pushing to GitHub:

```bash
# Install dependencies
pip install -r phase3_orchestration/requirements.txt
pip install -r phase2_agent_analysis/requirements.txt
pip install -r phase1_data_ingestion/requirements.txt
pip install instructor groq openai

# Set environment variables
export GROQ_API_KEY="your_api_key_here"

# Run pipeline
python phase3_orchestration/src/scheduler.py --mode run-now
```

### Security Considerations

- Never commit API keys or sensitive data to the repository
- Use GitHub Secrets for all sensitive configuration
- Review workflow logs for any accidental secret exposure
- Limit artifact retention to appropriate periods
- Use branch protection rules to control workflow modifications

### Customization

**Change schedule time:**
Modify the cron expression in `.github/workflows/weekly-pipeline.yml`:
```yaml
schedule:
  - cron: '30 4 * * 1'  # Change this to desired schedule
```

**Add more artifacts:**
Add additional paths to the artifact upload steps:
```yaml
- name: Upload custom artifacts
  uses: actions/upload-artifact@v4
  with:
    name: custom-artifacts
    path: path/to/your/files
```

**Change Python version:**
Modify the Python setup step:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # Change to desired version
```

### Monitoring

- Monitor workflow executions from the **Actions** tab
- Enable email notifications for workflow failures in repository settings
- Review workflow summaries for execution status
- Check artifacts for pipeline outputs

### Cost Considerations

- GitHub Actions provides free minutes for public repositories
- Private repositories have monthly limits based on plan
- Monitor usage in repository settings → Actions → Usage
- Optimize workflow steps to reduce execution time if needed

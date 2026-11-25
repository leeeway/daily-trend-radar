// Deploy the exact upload ID already verified by wait_pages_artifact.py.
// This avoids the separate artifact-name lookup failing on an existing upload.
module.exports = async function deployPages({github, core, context, artifactId, siteUrl,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), now = Date.now,
  timeoutMs = 600000}) {
  const id = Number(artifactId);
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Missing or invalid Pages artifact ID');
  const oidcToken = await core.getIDToken();
  core.setSecret(oidcToken);
  let deployment;
  try {
    ({data: deployment} = await github.request('POST /repos/{owner}/{repo}/pages/deployments', {
      ...context.repo, artifact_id: id, pages_build_version: context.sha, oidc_token: oidcToken
    }));
  } catch (error) {
    throw new Error(`Pages deployment creation failed (HTTP ${error.status || 'unavailable'})`);
  }
  const deploymentId = deployment.id || deployment.status_url?.split('/').pop() || context.sha;
  const params = {...context.repo, deployment_id: deploymentId};
  const deadline = now() + timeoutMs;
  const failures = new Set(['deployment_failed', 'deployment_content_failed', 'deployment_cancelled', 'deployment_lost']);
  let pending = true;
  let errors = 0;
  try {
    while (now() < deadline) {
      await sleep(5000);
      let status;
      try {
        ({data: {status}} = await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deployment_id}', params));
        errors = 0;
      } catch (error) {
        if ((error.status >= 400 && error.status < 500 && error.status !== 429) || ++errors >= 10) {
          throw new Error(`Cannot verify Pages deployment (HTTP ${error.status || 'unavailable'})`);
        }
        core.warning('Pages status request interrupted; retrying');
        continue;
      }
      core.info(`Pages deployment status: ${status}`);
      if (status === 'succeed') {
        pending = false;
        core.setOutput('page_url', siteUrl);
        core.setOutput('status', status);
        return;
      }
      if (failures.has(status)) {
        pending = false;
        throw new Error(`Pages deployment failed: ${status}`);
      }
    }
    throw new Error('Pages deployment timed out');
  } finally {
    if (pending) {
      try {
        await github.request('POST /repos/{owner}/{repo}/pages/deployments/{deployment_id}/cancel', params);
      } catch {
        core.warning('Unable to cancel unfinished Pages deployment');
      }
    }
  }
};

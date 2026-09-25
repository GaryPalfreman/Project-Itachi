# Google Drive and MEGA Recovery

Itachi can use a dedicated Google account and a dedicated MEGA account as optional recovery mirrors. These are server-side infrastructure accounts: visitors using the Streamlit app never need to sign into them and never receive their credentials.

## Google Drive

A personal Google Account currently includes up to 15 GB shared across Gmail, Drive and Photos. Create a dedicated account for Itachi manually in Google's account-creation flow.

Recommended naming pattern: `project.itachi.storage@...` or `itachi.recovery@...`. Do not reuse a personal account.

Then:

1. Create a Google Cloud project for Itachi.
2. Enable the Google Drive API.
3. Configure an OAuth consent screen and OAuth client.
4. Authorize that client once while signed in as the dedicated Itachi Google account, requesting Drive access.
5. Store the resulting OAuth refresh token in GitHub Actions secrets.
6. Optionally create an `Itachi Recovery` folder in Drive and save its folder ID.

Default recovery folder ID:

```
1fFi6bHUEgjU5cz9M9V8uYaNme1cGgX37
```

Required repository secrets:

```
ITACHI_GOOGLE_API_KEY
ITACHI_GOOGLE_CLIENT_ID
ITACHI_GOOGLE_CLIENT_SECRET
ITACHI_GOOGLE_REFRESH_TOKEN
ITACHI_GOOGLE_DRIVE_FOLDER_ID
```

The Google API key is sent only in the `x-goog-api-key` request header. It is never written to a URL, log message, source file, or browser bundle. The API key identifies the Google Cloud project but does not replace OAuth authorization for Drive writes.

The hourly workflow uploads:

```
public_catalog.json
public_knowledge.jsonl
state.json
```

It never commits Google credentials to the repository.

## MEGA

MEGA currently advertises a free plan with 20 GB storage in most regions, although regional availability or promotions can differ. Create a dedicated MEGA account using the Itachi email address and save its recovery key somewhere independent of the MEGA account.

Required repository secrets:

```
ITACHI_MEGA_EMAIL
ITACHI_MEGA_PASSWORD
```

GitHub Actions uses a temporary rclone configuration on the ephemeral runner, uploads the recovery tree, and deletes that temporary configuration when the step ends.

The destination is:

```
/Project-Itachi/recovery/
```

with the learned corpus under:

```
/Project-Itachi/recovery/knowledge/
```

## Recovery

The GitHub Action `Recover Itachi public knowledge` has a source selector:

- `supabase`
- `google-drive`
- `mega`

Choosing Google Drive or MEGA downloads the most recent public knowledge snapshot and commits it back into the repository.

## Security

Do not put account passwords, OAuth client secrets, refresh tokens or recovery keys into source files, Streamlit UI fields, public issues, or README examples. Keep them in GitHub Actions/Streamlit secrets.

The Google and MEGA accounts are recovery infrastructure, not user identity. Public Streamlit visitors should never receive direct access to either account.


## Streamlit OAuth bootstrap

The deployed app at `https://project-itachi.streamlit.app` can perform the one-time Google OAuth authorization.

Recommended Streamlit secret:

```toml
ITACHI_GOOGLE_OAUTH_JSON = '''PASTE_THE_COMPLETE_GOOGLE_WEB_CLIENT_JSON_HERE'''
```

The app parses the client ID, client secret and redirect URI server-side. The secret JSON is never rendered or committed.

After unlocking Itachi with `ITACHI_ACCESS_PASSCODE`, open **Google Drive admin** in the sidebar and choose **Connect Itachi Google Drive**. Google returns to the same Streamlit URL. Itachi validates the signed state and exchanges the authorization code server-side.

If Google returns a refresh token, copy it once into the GitHub Actions repository secret:

```
ITACHI_GOOGLE_REFRESH_TOKEN
```

For GitHub Actions, you may also store the same complete OAuth JSON as:

```
ITACHI_GOOGLE_OAUTH_JSON
```

The backup/recovery scripts accept this single JSON secret, so separate client ID/client secret values are optional.

The OAuth request uses `https://www.googleapis.com/auth/drive.file`, `access_type=offline` and `prompt=consent`. If the pre-existing recovery folder is not visible under the narrow `drive.file` grant, Itachi creates and reuses an app-owned `Project-Itachi-Recovery` folder instead of failing.

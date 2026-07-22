description = """
## Applications

A valid access token is required to perform the below requests.

### Caseworkers
Authorised caseworkers can:

* Read all applications by sending a get request to **/applications/**.
* Read a given application by sending a get request to **/applications/{laa_reference}**.
* Read the evidence associated with an application by sending a get request to **/applications/{laa_reference}/coroners-letter**.
* Update the merits decision for an application to refused by sending a patch request to **/applications/{laa_reference}/refuse-decision**.
* Update the merits decision for an application to granted by sending a patch request to **/applications/{laa_reference}/grant-decision**.

### Providers
Authorised providers can:
* Create an application by posting to **/applications/**.
* Create a claim by posting to **/applications/{laa_reference}/claim**.
* Upload evidence by posting to **/applications/coroners-letter**.
* Search for an application by LAA reference by sending a get request to **/applications/search**.


## Notifications

Used by GovNotify for changes in status of notification delivery.
"""

docs_config = {
    "title": "LAA Inquests API",
    "description": description,
    "summary": "API for managing Inquests related legal aid applications. Used by Inquests External UI and Inquests Internal UI.",
    "version": "0.0.1",
    "contact": {
        "name": "Civil Legal Advice",
    },
    "license_info": {
        "name": "MIT Licence",
        "url": "https://github.com/ministryofjustice/laa-inquests-api/blob/main/LICENSE",
    },
    "docs_url": "/",
}

# Getting Started with QuillShield

QuillShield is a comprehensive Web3 DevSecOps platform that provides AI-driven security audits to enhance smart contract integrity and resilience.&#x20;

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FYN4MvVTt3p9oPgr3dlZO%2FQuillShield.png?alt=media&#x26;token=00d05dbd-978e-4d9b-a49b-1036fd755978" alt=""><figcaption></figcaption></figure>


# Project Upload Methods

QuillShield supports three distinct methods for uploading smart contracts for audit:

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2F21yp8LAgXVEsSe326xaO%2FScreenshot%202025-04-24%20031303.png?alt=media&#x26;token=5374385a-e954-4fee-ab72-ddd9b4dbef7c" alt=""><figcaption></figcaption></figure>

{% content-ref url="project-upload-methods/import-from-verified-contract" %}
[import-from-verified-contract](https://quillainetwork.gitbook.io/shield/project-upload-methods/import-from-verified-contract)
{% endcontent-ref %}

{% content-ref url="project-upload-methods/upload-from-device" %}
[upload-from-device](https://quillainetwork.gitbook.io/shield/project-upload-methods/upload-from-device)
{% endcontent-ref %}

{% content-ref url="project-upload-methods/import-from-github" %}
[import-from-github](https://quillainetwork.gitbook.io/shield/project-upload-methods/import-from-github)
{% endcontent-ref %}


# Import from Verified Contract

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FhozsjFQhr7T1j3ohYy3Z%2Fimage.png?alt=media&#x26;token=bbb55808-d49c-4265-96f1-4c3af5296cf3" alt=""><figcaption></figcaption></figure>

This method allows you to audit contracts that are already deployed and verified on blockchain explorers:

* Copy the contract address from scanners like **Etherscan**
* Paste the address in QuillShield under "Import from Verified Contract"
* Select your target **network** (e.g., Ethereum, Polygon, BSC)
* Provide a descriptive **project name**
* QuillShield automatically fetches the contract source code, compiles it, and checks for dependencies


# Upload from Device

For contracts stored locally on your system:

* Upload individual `.sol` files or complete zipped project folders
* Ideal for contracts that aren't yet deployed or verified online
* Supports drag-and-drop functionality for ease of use
* Maintains folder structure for complex projects

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2F9S02HM4cbTBrFnkoSvUf%2Fimage.png?alt=media&#x26;token=ab4d9014-d095-4f65-ad32-cc16a44bd5dc" alt=""><figcaption></figcaption></figure>


# Import from GitHub

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FaMobZ8YYVvnMjJzormPy%2Fimage.png?alt=media&#x26;token=669be3b1-b0c8-4e04-a64c-2d9626b32e74" alt=""><figcaption></figcaption></figure>

Direct integration with GitHub repositories:

* Paste your **GitHub repository URL**
* Select the specific branch you want to audit
* Choose which folders to include in the audit (selective inclusion supported)
* Particularly useful for ongoing development projects with version control


# Handling Incomplete Projects

QuillShield includes robust dependency management to handle incomplete or misconfigured projects:

### Dependency Detection

* Automatically identifies missing files or dependencies during compilation
* Provides clear notifications about missing components (e.g., console.sol, OpenZeppelin imports)
* Displays compilation errors with specific file references

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FxFeViwCzW0XrQpQ7DcIm%2Fimage.png?alt=media&#x26;token=a5c0b820-c441-4001-811e-ecc25e0036ca" alt=""><figcaption></figcaption></figure>

Manual Resolution

* Upload missing files directly through the platform interface
* Adjust Solidity compiler versions to resolve compatibility issues
* Use the "Apply Fixer" button to re-run compilation after resolving dependencies

### Compiler Version Management

QuillShield handles projects with mismatched Solidity compiler versions:

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2F5xu2nXZUQcodp8JRyApW%2FScreenshot%202025-05-15%20122701.png?alt=media&#x26;token=cdd5b684-6d9a-4828-a7ca-740ff29f3382" alt=""><figcaption></figcaption></figure>

* Error Detection: Flags version mismatches during project upload (e.g., files using 0.8.0 vs 0.8.29)
* Resolution: Manual adjustment of compiler versions through the UI
* Validation: Ensures successful compilation before proceeding to audit


# Audit Configuration and Execution

### Audit Setup

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FKB4rTMdeWpUZn99cdn3t%2Fimage.png?alt=media&#x26;token=5d7a14b9-703c-4234-bd1c-c8f4c8828e9d" alt=""><figcaption></figcaption></figure>

Once your project is successfully uploaded and compiled:

1. Click "Audit Now" to begin the process
2. Select specific files or audit the entire project
3. Choose whether to include Business Logic Analysis
4. Specify relevant Contract Standards (ERC20, ERC721, etc.)

### Credit System

* Each line of code consumes 1 credit
* Example: A 32-line contract deducts 32 credits
* Starting allocation: 2,000 free credits
* Audit duration: Typically 1-2 minutes depending on project complexity


# Audit Analysis Types

### Standard Smart Contract Auditing

Focuses on common vulnerability patterns:

* Reentrancy attacks
* Integer overflow/underflow
* Access control issues

### ERC Token Standard Detection

Specialized analysis for token contracts:

ERC-20 Detector:

* Missing return values in transfer functions
* Approval race conditions
* Interface compliance verification
* Standard-specific security patterns

ERC-721 Detector:

* NFT-specific vulnerabilities
* Metadata handling issues
* Transfer mechanism validation

### Advanced Business Logic Analysis

Comprehensive deep-logic evaluation:

* Function call tree analysis (internal/external calls)
* State variable interaction mapping
* Privilege escalation risk assessment
* Complex contract interaction patterns
* Centralized control risk identification


# Understanding Audit Reports

### Severity Classification

Findings are categorized by risk level:

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2FtMfO0u46athK7S2d7DRK%2Fimage.png?alt=media&#x26;token=cd38ea95-e670-4613-a36a-4bc990e211d6" alt=""><figcaption></figcaption></figure>

* 🔴 High: Critical vulnerabilities requiring immediate attention
* 🟡 Medium: Significant issues that should be addressed
* 🟢 Low: Minor concerns or best practice recommendations
* 🟣Informational: Minor concerns or best practice recommendations

### Issue Documentation

<figure><img src="https://2615096420-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F7GSEJHxHSUllIfuVOsH5%2Fuploads%2F9XSZ1xBrX3A99BreDJX8%2Fimage.png?alt=media&#x26;token=7051fd37-e3bf-4ca3-8835-c004ef977736" alt=""><figcaption></figcaption></figure>

Each finding includes:

* Detailed description of the vulnerability
* Location within the codebase
* Potential impact assessment
* Recommended remediation steps

### Proof of Concept (POC)

Selected vulnerabilities include POCs that demonstrate:

* Step-by-step exploitation process
* Potential attack vectors
* Impact scenarios

Future updates will provide:

* Attacker contract examples
* Local simulation capabilities


# Best Practices for Using QuillShield

### Pre-Audit Preparation

* Ensure all dependencies are properly configured
* Use consistent Solidity compiler versions across your project
* Organize your codebase with clear folder structures
* Document any custom business logic for better analysis

### Interpreting Results

* Prioritize High and Medium severity findings
* Review Low severity issues for code quality improvements
* Validate findings against your specific use case requirements
* Consider the provided POCs for understanding attack vectors


# Quality Assurance and Feedback

### False Positive Reporting

QuillShield includes mechanisms for continuous improvement:

* Telegram integration for direct bug reporting
* Community feedback collection through embedded links
* AI model refinement based on user input

### Continuous Learning Framework

QuillShield employs reinforcement learning to improve accuracy:

* Learns from each contract reviewed
* Adapts to new threat patterns
* Incorporates community feedback for model enhancement


# QuillShield API

This QuillShield API provides a simple REST interface to our state-of-the-art smart contract auditing platform. This document outlines how you can use our HTTP APIs in your customized app workflows.


# Authentication

To authenticate any request in the QuillShield API, you must pass the x-api-key in the header of all your requests to the domain shield-api-dev.quillaudits.com.

### Here's How to Get Started

### Step 1: 🔑Request an API key by contacting the team via <product@quillai.network>.

### Step 2: 🎉 Make Your First Request

{% hint style="info" %}
📑 Replace **"`YOUR_API_KEY"`** with your **API Key,** which was received by completing Step 1.
{% endhint %}

#### Example 1: via CURL from a command line

```
curl -H "x-api-key: YOUR_API_KEY" https://shield-api.quillai.network/api/v1/projects/list
```


# Api Reference


# Upload Project

To upload a project, you need to initiate a GET request to the following URL, with 'fileName' as the input parameter.\
\ <mark style="color:blue;">`GET`</mark> <https://shield-api.quillai.network/api/v1/projects/upload/url>

{% tabs %}
{% tab title="200 Project Url Fetched" %}

<pre class="language-javascript"><code class="lang-javascript"><strong>{
</strong>    "uploadUrl": "https://shield-dev-project-files.s3.ap-south-1.amazonaws.com/Project-235b374cb8647ab9df9ade037f896b45-abc.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&#x26;X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&#x26;X-Amz-Credential=AKIAXEQYZVJYL32YLXEH%2F20240826%2Fap-south-1%2Fs3%2Faws4_request&#x26;X-Amz-Date=20240826T080541Z&#x26;X-Amz-Expires=300&#x26;X-Amz-Signature=00a6df0911ba3025e8bcd5d31800bfb7e8bdbd904eef880e0587e58346d68849&#x26;X-Amz-SignedHeaders=host&#x26;x-id=PutObject",
    "uploadId": "Project-235b374cb8647ab9df9ade037f896b45-abc.zip"
}
</code></pre>

{% endtab %}

{% tab title="400 Bad Request" %}

```javascript
{
    "message": "must have required property 'fileName'"
}
```

{% endtab %}
{% endtabs %}

The resulting "uploadUrl" from the API is where you'll be uploading all your files to, in the form of a 'PUT' request. The files must strictly either be either zip archives or solidity contracts.

### Query Parameters

<table><thead><tr><th width="148">Parameter</th><th width="306">Description</th><th width="102">Data Type</th><th>Requirement</th></tr></thead><tbody><tr><td>fileName</td><td>Name of file to be uploaded along with filetype ( .sol or .zip)</td><td>String</td><td>Required</td></tr></tbody></table>

### Response Codes

| Responses | Description  |
| --------- | ------------ |
| 🟢 200    | Success      |
| 🟠 400    | Error        |
| 🔴 401    | Unauthorised |

### Sample Response

```javascript
{
    "uploadUrl": "https://shield-dev-project-files.s3.ap-south-1.amazonaws.com/Project-235b374cb8647ab9df9ade037f896b45-abc.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAXEQYZVJYL32YLXEH%2F20240826%2Fap-south-1%2Fs3%2Faws4_request&X-Amz-Date=20240826T080541Z&X-Amz-Expires=300&X-Amz-Signature=00a6df0911ba3025e8bcd5d31800bfb7e8bdbd904eef880e0587e58346d68849&X-Amz-SignedHeaders=host&x-id=PutObject",
    "uploadId": "Project-235b374cb8647ab9df9ade037f896b45-abc.zip"
}
```


# Audit Project

<mark style="color:blue;">`POST`</mark> [https://shield-api.quillai.network/api/v1/projects/audit](ttps://shield-api.quillai.network/api/v1/projects/audit)

You can initiate an audit by performing a GET request and passing in your userId and projectId details to the request. Depending upon the size of the project, an audit can take anywhere between 10 seconds to even a minute.

```javascript
const fetchAuditDetails = async (projectId, userId, apiKey) => {
    const url = `https://shield-api.quillai.network/api/v1/projects/audit`;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'x-api-key': apiKey
            },
            body: JSON.stringify({uploadId={uploadId}&userId=${userId}})
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const auditData = await response.json();
        
        // Log the details from the response
        console.log("Total Lines of Code:", auditData.totalLines);
        console.log("Audited Files:", auditData.auditedFiles);
        console.log("Security Score:", auditData.securityScore);
        console.log("Vulnerability Count:", auditData.vulnerabilityCount);
        console.log("Vulnerabilities:", auditData.vulnerabilities);

        // Log the project report link
        console.log("Project Report Link:", auditData.projectReportLink);

    } catch (error) {
        console.error("Failed to fetch audit details:", error);
    }
};

// Example usage:
const projectId = 'your-project-id';
const userId = 'your-user-id';
const apiKey = 'your-api-key';

fetchAuditDetails(projectId, userId, apiKey);



```

{% tabs %}
{% tab title="200 Audit Done" %}

<pre class="language-javascript"><code class="lang-javascript"><strong>{
</strong>    "totalLines": 707,
    "auditedFiles": 5,
    "securityScore": "97.69",
    "vulnerabilityCount": {
        "high": 0,
        "medium": 0,
        "low": 2,
        "informational": 0,
        "optimization": 0
    },
    "vulnerabilities": {
        "high": [],
        "medium": [],
        "low": [
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the local variable 'owner' in the 'increaseAllowance' and 'decreaseAllowance' functions should be renamed to avoid shadowing the 'owner' function of the 'Ownable' contract. This can prevent confusion and potential bugs that may arise from the overloading of the 'owner' function. For instance, the local variable 'owner' could be renamed to 'functionOwner' or something similar.",
                "explanation": "The issue reported is a shadowing of the 'owner' function within the 'Ownable' contract by the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract. In Solidity, a function can be overloaded within the same contract, but this can lead to confusion and potential bugs if not used carefully. In this case, the 'owner' function in the 'Ownable' contract is a public function that returns the owner's address, and the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract is a local variable that shadows the 'owner' function, which is not intended.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the variable declaration 'address owner = _msgSender();' in the 'transfer' function should be renamed to avoid shadowing the 'owner()' function. A common convention is to use a prefix like 'msgSender' for variables that represent the message sender, which would make the intention clearer and avoid shadowing conflicts.",
                "explanation": "The 'owner()' function in the 'Ownable' contract is being shadowed by a variable declaration with the same name in the 'transfer' function of the 'GrinchCoin' contract. This can lead to confusion and potential bugs when the 'owner()' function is intended to be called, but the compiler or reader interprets it as a reference to the 'owner' variable declared in the 'transfer' function. This issue is confirmed by the static analysis report which identifies the 'shadowing-local' vulnerability.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            }
        ],
        "informational": [],
        "optimization": []
    },
    "projectReportLink": "https://quillshield-git-dev-front-qa.vercel.app/testzip/shareablelink/819824988da830d72be8519a9d2887773b9608be27c901f01598a2a9588a199a?type=3&#x26;projectID=11"
}
</code></pre>

{% endtab %}

{% tab title="400 Bad Request" %}

```javascript
{
    "message": "must have required property 'userId'"
}
```

{% endtab %}
{% endtabs %}

### Query Parameters

This route takes three query parameters, 'uploadId', 'userId' and 'name'. 'uploadId' is the id of the uploaded project, and can be taken from the upload project api. UserId is helpful in mapping users of your platform to QuillShield and maintaining their separate audit history, it can be any unique Identifier (wallet address, email etc). The 'name' parameter is an optional param, which is used to name the project.

<table><thead><tr><th width="511">Parameter</th><th width="306">Description</th><th width="102">Data Type</th><th>Requirement</th></tr></thead><tbody><tr><td>uploadId</td><td>Project Id created</td><td>String</td><td>Required</td></tr><tr><td>userId</td><td>User Identifier</td><td>String</td><td>Required</td></tr><tr><td>name</td><td>Project Name</td><td>String</td><td>Optional</td></tr></tbody></table>

### Response Codes

| Responses | Description  |
| --------- | ------------ |
| 🟢 200    | Success      |
| 🟠 400    | Error        |
| 🔴 401    | Unauthorised |

### Sample Response

```javascript
{
    "totalLines": 707,
    "auditedFiles": 5,
    "securityScore": "97.69",
    "vulnerabilityCount": {
        "high": 0,
        "medium": 0,
        "low": 9,
        "informational": 0,
        "optimization": 0
    },
    "vulnerabilities": {
        "high": [],
        "medium": [],
        "low": [
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the local variable 'owner' in the 'increaseAllowance' and 'decreaseAllowance' functions should be renamed to avoid shadowing the 'owner' function of the 'Ownable' contract. This can prevent confusion and potential bugs that may arise from the overloading of the 'owner' function. For instance, the local variable 'owner' could be renamed to 'functionOwner' or something similar.",
                "explanation": "The issue reported is a shadowing of the 'owner' function within the 'Ownable' contract by the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract. In Solidity, a function can be overloaded within the same contract, but this can lead to confusion and potential bugs if not used carefully. In this case, the 'owner' function in the 'Ownable' contract is a public function that returns the owner's address, and the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract is a local variable that shadows the 'owner' function, which is not intended.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the variable declaration 'address owner = _msgSender();' in the 'transfer' function should be renamed to avoid shadowing the 'owner()' function. A common convention is to use a prefix like 'msgSender' for variables that represent the message sender, which would make the intention clearer and avoid shadowing conflicts.",
                "explanation": "The 'owner()' function in the 'Ownable' contract is being shadowed by a variable declaration with the same name in the 'transfer' function of the 'GrinchCoin' contract. This can lead to confusion and potential bugs when the 'owner()' function is intended to be called, but the compiler or reader interprets it as a reference to the 'owner' variable declared in the 'transfer' function. This issue is confirmed by the static analysis report which identifies the 'shadowing-local' vulnerability.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the local variable 'owner' in the 'decreaseAllowance' and 'increaseAllowance' functions should be renamed to avoid shadowing the 'owner()' function from the 'Ownable' contract. It is a best practice to use a naming convention that clearly differentiates between state variables and local variables, such as prefixing state variables with '_' or 'this'.",
                "explanation": "The warning 'shadowing-local' indicates that a variable or function within the contract has the same name as a variable or function in a parent contract, which could lead to confusion and potentially cause bugs. In this case, the 'owner()' function in the 'Ownable' contract is being shadowed by the 'owner' local variable within the 'decreaseAllowance' and 'increaseAllowance' functions. This is due to the fact that in Solidity, local variables take precedence over state variables with the same name.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the local variable 'owner' in the 'decreaseAllowance' function should be renamed to avoid shadowing the 'owner' function from the 'Ownable' contract. For example, the variable could be renamed to 'sender' to reflect its purpose more clearly.",
                "explanation": "The issue reported is a shadowing of the 'owner' function within the 'Ownable' contract by the 'owner' variable in the 'decreaseAllowance' function of the 'GrinchCoin' contract. This means that the local variable 'owner' in 'decreaseAllowance' is hiding the 'owner' function of the 'Ownable' contract, which can lead to confusion and potential bugs when attempting to access the 'owner' function.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the variable in the 'approve' function should be renamed to something that does not conflict with the 'owner()' function, such as 'ownerAddress'. This will prevent the shadowing and make the code clearer and less error-prone.",
                "explanation": "The function 'owner()' in the Ownable contract is being shadowed by a variable with the same name in the approve function of the GrinchCoin contract. This can lead to confusion and potentially to errors if the 'owner' variable were to be used instead of the 'owner()' function, as it would refer to the shadowed variable within the scope of the 'approve' function.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the parameter name 'owner' in the '_spendAllowance' function should be changed to a name that does not conflict with the function names or variable names of the 'Ownable' contract, such as 'ownerAddress'. This change will clarify the intention of the parameter and avoid any potential shadowing issues.",
                "explanation": "The static analysis report indicates that there is a function 'owner()' in the 'Ownable' contract that is being shadowed by a variable with the same name in the '_spendAllowance' function of the 'GrinchCoin' contract. This is a legitimate finding, as within the '_spendAllowance' function, the parameter 'owner' has the same name as the 'owner()' function in the 'Ownable' contract. This can be potentially confusing and may lead to errors when the contract is being interacted with, as the 'owner' variable within the function will take precedence over the 'owner()' function of the contract.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Local Variables Being Shadowed",
                "severity": "low",
                "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                "lineNumbers": [
                    64,
                    66
                ],
                "confidence": "high",
                "recommendation": "To resolve this issue, the local variable in the 'approve' function should be renamed to avoid shadowing the 'owner' function from the Ownable contract. For example, the local 'owner' variable in the 'approve' function could be renamed to 'sender' to make it clear that it's referring to the sender of the message.",
                "explanation": "The 'owner' function in the Ownable contract is being shadowed by a local variable with the same name within the 'approve' function of the GrinchCoin contract. This means that within the 'approve' function, any reference to 'owner' is resolved to the locally declared variable, which can lead to unexpected behavior and potential security risks if not used properly.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Missing Zero Address Validation",
                "severity": "low",
                "snippet": "v2Pair = _v2Pair;",
                "lineNumbers": [
                    147,
                    147
                ],
                "confidence": "medium",
                "recommendation": "To mitigate this issue, the setUniswapPair function should include a requirement that the '_v2Pair' parameter is not the zero address before assigning it to 'v2Pair'. This is commonly done using the 'require' statement to enforce a condition. For example: require(_v2Pair != address(0), 'setUniswapPair: v2Pair cannot be the zero address');",
                "explanation": "The provided smart contract code for GrinchCoin's setUniswapPair function does not include a check to ensure that the '_v2Pair' parameter is not the zero address. The 'v2Pair' state variable is assigned the value of '_v2Pair' without any validation that the address is not the zero address (0x0000000000000000000000000000000000000000). Assigning a critical functionality address or token pair to the zero address could lead to a loss of funds or make the contract unusable.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            },
            {
                "name": "Missing Zero Address Validation",
                "severity": "low",
                "snippet": "tokenPairAddress = _tokenPairAddress;",
                "lineNumbers": [
                    146,
                    146
                ],
                "confidence": "medium",
                "recommendation": "To ensure that the '_tokenPairAddress' is not the zero address, the function should include a check that the address is not equal to the zero address before assigning it to 'tokenPairAddress'.",
                "explanation": "The provided smart contract code for GrinchCoin's 'setUniswapPair' function does not include a zero-address check for the '_tokenPairAddress' parameter before assigning it to the 'tokenPairAddress' state variable. This means that if the '_tokenPairAddress' passed to the function is the zero address (0x000...000), the contract will accept it as a valid Uniswap pair address, which is not a valid or intended behavior in the context of setting an actual token pair.",
                "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
            }
        ],
        "informational": [],
        "optimization": []
    },
    "projectReportLink": "https://quillshield-git-dev-front-qa.vercel.app/testzip/shareablelink/819824988da830d72be8519a9d2887773b9608be27c901f01598a2a9588a199a?type=3&projectID=11"
}
```

### Requesting Data in Markdown Formatting

If you intend on integrating onchain agents with our platform, the QuillShield API can make the process quite comfortable by providing you the data in markdown Format. To get data in a markdown format, you can simple add a 'format' parameter to the above request. Here's a more clear example:\
\ <mark style="color:blue;">`POST`</mark> [https://shield-api.quillai.network/api/v1/projects/audit](https://app.gitbook.com/o/q2TLKxsHPZc4IWsVo3vM/s/7GSEJHxHSUllIfuVOsH5/)?format=MD

And that's it, by adding that parameter you can query data in markdown format. The request data would follow the same response schema as shown previously with an addition of the 'markdown' attribute which contains the audit report in the markdown format

The response would be structured like this

{% code overflow="wrap" %}

```json
{
  "totalLines": <number>,
  "auditedFiles": <number>,
  "markdown": <string>,
  "securityScore": <string>,
  "vulnerabilityCount": {
    "high": <number>,
    "medium": <number>,
    "low": <number>,
    "informational": <number>,
    "optimization": <number>
  },
  "vulnerabilities": {
    "high": [
      {
        "name": <string>,
        "severity": <string>,
        "snippet": <string>,
        "lineNumbers": [<number>, <number>],
        "confidence": <string>,
        "recommendation": <string>,
        "explanation": <string>,
        "file": <string>
      }
    ],
    "medium": [
      {
        "name": <string>,
        "severity": <string>,
        "snippet": <string>,
        "lineNumbers": [<number>, <number>],
        "confidence": <string>,
        "recommendation": <string>,
        "explanation": <string>,
        "file": <string>
      }
    ],
    "low": [
      {
        "name": <string>,
        "severity": <string>,
        "snippet": <string>,
        "lineNumbers": [<number>, <number>],
        "confidence": <string>,
        "recommendation": <string>,
        "explanation": <string>,
        "file": <string>
      }
    ],
    "informational": [
      {
        "name": <string>,
        "severity": <string>,
        "snippet": <string>,
        "lineNumbers": [<number>, <number>],
        "confidence": <string>,
        "recommendation": <string>,
        "explanation": <string>,
        "file": <string>
      }
    ],
    "optimization": [
      {
        "name": <string>,
        "severity": <string>,
        "snippet": <string>,
        "lineNumbers": [<number>, <number>],
        "confidence": <string>,
        "recommendation": <string>,
        "explanation": <string>,
        "file": <string>
      }
    ]
  },
  "projectReportLink": <string>
}

```

{% endcode %}


# Get Project Audits

The folllowing endpoint lets you query all audits related to a project. You can adjust the paging paramaters to limit the information that's provided to you.

<mark style="color:blue;">`GET`</mark> <https://shield-api.quillai.network/api/v1/projects/audit/history>

{% tabs %}
{% tab title="200 Audits Found" %}

```javascript
{
    "audits": [
        {
            "totalLines": 707,
            "securityScore": 97.69,
            "vulnerabilityCount": {
                "high": 0,
                "medium": 0,
                "low": 3,
                "informational": 0,
                "optimization": 0
            },
            "vulnerabilities": [
                {
                    "name": "Local Variables Being Shadowed",
                    "severity": "low",
                    "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                    "lineNumbers": [
                        64,
                        66
                    ],
                    "confidence": "high",
                    "recommendation": "To resolve this issue, the variable in the 'approve' function should be renamed to something that does not conflict with the 'owner()' function, such as 'ownerAddress'. This will prevent the shadowing and make the code clearer and less error-prone.",
                    "explanation": "The function 'owner()' in the Ownable contract is being shadowed by a variable with the same name in the approve function of the GrinchCoin contract. This can lead to confusion and potentially to errors if the 'owner' variable were to be used instead of the 'owner()' function, as it would refer to the shadowed variable within the scope of the 'approve' function.",
                    "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
                },
                {
                    "name": "Local Variables Being Shadowed",
                    "severity": "low",
                    "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                    "lineNumbers": [
                        64,
                        66
                    ],
                    "confidence": "high",
                    "recommendation": "To resolve this issue, the local variable 'owner' in the 'increaseAllowance' and 'decreaseAllowance' functions should be renamed to avoid shadowing the 'owner' function of the 'Ownable' contract. This can prevent confusion and potential bugs that may arise from the overloading of the 'owner' function. For instance, the local variable 'owner' could be renamed to 'functionOwner' or something similar.",
                    "explanation": "The issue reported is a shadowing of the 'owner' function within the 'Ownable' contract by the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract. In Solidity, a function can be overloaded within the same contract, but this can lead to confusion and potential bugs if not used carefully. In this case, the 'owner' function in the 'Ownable' contract is a public function that returns the owner's address, and the 'owner' variable within the 'increaseAllowance' and 'decreaseAllowance' functions of the 'GrinchCoin' contract is a local variable that shadows the 'owner' function, which is not intended.",
                    "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
                },
                {
                    "name": "Local Variables Being Shadowed",
                    "severity": "low",
                    "snippet": "function owner() public view returns (address) {\r\n        return _owner;\r\n    }",
                    "lineNumbers": [
                        64,
                        66
                    ],
                    "confidence": "high",
                    "recommendation": "To resolve this issue, the variable declaration 'address owner = _msgSender();' in the 'transfer' function should be renamed to avoid shadowing the 'owner()' function. A common convention is to use a prefix like 'msgSender' for variables that represent the message sender, which would make the intention clearer and avoid shadowing conflicts.",
                    "explanation": "The 'owner()' function in the 'Ownable' contract is being shadowed by a variable declaration with the same name in the 'transfer' function of the 'GrinchCoin' contract. This can lead to confusion and potential bugs when the 'owner()' function is intended to be called, but the compiler or reader interprets it as a reference to the 'owner' variable declared in the 'transfer' function. This issue is confirmed by the static analysis report which identifies the 'shadowing-local' vulnerability.",
                    "file": "GrinchCoin/src/backend/contracts/FeesHiddenV13/GrinchCoin.sol"
                }
            ],
            "projectReportLink": "https://quillshield-git-dev-front-qa.vercel.app/testzip/shareablelink/819824988da830d72be8519a9d2887773b9608be27c901f01598a2a9588a199a?type=3&projectID=11"
        }
    ],
    "auditCount": 2
}
```

{% endtab %}

{% tab title="400 Bad Request" %}

```javascript
{
    "message": "must have required property 'userId'"
}
```

{% endtab %}
{% endtabs %}

### Query Parameters

<table><thead><tr><th width="148">Parameter</th><th width="306">Description</th><th width="102">Data Type</th><th>Requirement</th></tr></thead><tbody><tr><td>projectId</td><td>Id of project created</td><td>String</td><td>Required</td></tr><tr><td>userId</td><td>User identifier</td><td>String</td><td>Required</td></tr><tr><td>limit</td><td>Limit count for number of records</td><td>String</td><td>Optional</td></tr><tr><td>page</td><td>page number for pagination</td><td>String</td><td>Optional</td></tr></tbody></table>

### Response Codes

| Responses | Description  |
| --------- | ------------ |
| 🟢 200    | Success      |
| 🟠 400    | Error        |
| 🔴 401    | Unauthorised |

### Sample Response


# Get Projects

This endpoint allows you to query all projects associated to your userId.

<mark style="color:blue;">`GET`</mark> <https://shield-api.quillai.network/api/v1/projects/list>

{% tabs %}
{% tab title="200 Projects Found" %}

```javascript
{
    "projects": [
        {
            "name": "testingzip",
            "id": 12
        },
        {
            "name": "testzip",
            "id": 11
        }
    ],
    "totalProjects": 2
}
```

{% endtab %}

{% tab title="400 Bad Request" %}

```javascript
{
    "message": "must have required property 'userId'"
}
```

{% endtab %}
{% endtabs %}

### Query Parameters

<table><thead><tr><th width="148">Parameter</th><th width="306">Description</th><th width="102">Data Type</th><th>Requirement</th></tr></thead><tbody><tr><td>userId</td><td>Id of the user for which you want to query the projects</td><td>String</td><td>Required</td></tr><tr><td>limit</td><td>Limt count for number of records per page</td><td>String</td><td>Optional</td></tr><tr><td>page</td><td>Page Number for pagination</td><td>String</td><td>Optional</td></tr></tbody></table>

### Response Codes

| Responses | Description  |
| --------- | ------------ |
| 🟢 200    | Success      |
| 🟠 400    | Error        |
| 🔴 401    | Unauthorised |

### Sample Response

```javascript
{
    "projects": [
        {
            "name": "testingzip",
            "id": 12
        },
        {
            "name": "testzip",
            "id": 11
        }
    ],
    "totalProjects": 2
}
```



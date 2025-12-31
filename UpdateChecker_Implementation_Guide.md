# Universal Update Checker Implementation Guide

This document contains all necessary instructions, code snippets, and logic explanations to implement a "README-based" update checker in any C# WinForms application. 

**Agent Instruction:** Use the code blocks below to implement an update checker that compares the local application version against a version number string located in the `README.md` file of a GitHub repository.

---

## 1. Core Logic Class (Web Client)
First, we need a WebClient wrapper to handle timeouts and encoding correctly. This ensures the app doesn't hang if the internet is slow.

**Action:** Create a class file named `UpdateWebClient.cs` (or add this class to your namespace).

```csharp
using System;
using System.Net;
using System.Text;

namespace YourNamespace // CHANGE THIS to match project namespace
{
    // A simple wrapper around WebClient to enforce UTF8 and Timeouts
    public class UpdateWebClient : WebClient
    {
        private int timeout = 5000; // 5 seconds timeout

        public UpdateWebClient()
        {
            this.Encoding = Encoding.UTF8;
            this.Proxy = null; // Disable proxy for speed
        }

        public UpdateWebClient(int _timeout)
        {
            this.Encoding = Encoding.UTF8;
            this.Proxy = null;
            this.timeout = _timeout;
        }

        protected override WebRequest GetWebRequest(Uri address)
        {
            WebRequest request = base.GetWebRequest(address);
            if (request != null)
            {
                request.Timeout = timeout;
            }
            return request;
        }
    }
}
```

---

## 2. Configuration & Constants
Define these variables in your main `Form` class or a global `Program/Config` class.

**Action:** Add these fields to your class.

```csharp
// The current version of THIS software running on the user's machine
// TODO: Update this string whenever you release a new version.
public const string CurrentVersion = "v1.0.0"; 

// List of GitHub repositories to check (can be just one)
// Format: "https://github.com/Username/RepoName"
public readonly List<string> RemoteRepositories = new List<string>() 
{ 
    "https://github.com/YourUsername/YourRepoName" 
};

// The relative path to the file containing the version info (usually README.md)
// This points to the raw file content.
public const string UpdateFilePath = "/raw/main/README.md"; 

// The specific text to look for in the README file.
// The updater looks for a line starting with this, and parses the version number at the end.
// Example line in README: "My App Name v1.0.1"
public const string AppNameInReadme = "Your App Name"; 
```

---

## 3. The Update Logic Method
This method performs the check. It runs on a background thread to keep the UI responsive.

**Action:** Copy this method into your `MainForm.cs` (or logic controller).

```csharp
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Diagnostics; // For Process.Start

private int PerformUpdateCheck(Control triggeringControl)
{
    try
    {
        using (UpdateWebClient wc = new UpdateWebClient())
        {
            string bestUrl = "";
            float highestVersion = 0;
            float currentVersionNum = 0;

            // Parse local version (remove 'v')
            float.TryParse(CurrentVersion.Replace("v", ""), out currentVersionNum);

            foreach (var repoUrl in RemoteRepositories)
            {
                try 
                {
                    // Download the README
                    string rawContent = wc.DownloadString(repoUrl + UpdateFilePath);
                    
                    if (!string.IsNullOrEmpty(rawContent))
                    {
                        // Get the first line (or scan lines) where version info is expected
                        string firstLine = rawContent.Split('\n')[0]; 

                        // Check if the line contains our App Name
                        if (firstLine.Contains(AppNameInReadme))
                        {
                            // Logic: Split by space, take the last element, remove 'v', parse as float
                            // Expected format in README: "## My App Name v1.0.2"
                            string[] parts = firstLine.Split(' ');
                            string versionString = parts[parts.Length - 1].Trim();
                            
                            float foundVersion;
                            if (float.TryParse(versionString.Replace("v", ""), out foundVersion))
                            {
                                if (foundVersion > highestVersion)
                                {
                                    highestVersion = foundVersion;
                                    bestUrl = repoUrl;
                                }
                            }
                        }
                    }
                }
                catch (Exception loopEx) 
                { 
                    // Log error or ignore failed repo check
                    Debug.WriteLine($"Failed to check repo {repoUrl}: {loopEx.Message}");
                }
            }

            // Compare versions
            if (!string.IsNullOrEmpty(bestUrl) && highestVersion > currentVersionNum)
            {
                string newVersionStr = "v" + highestVersion;
                
                // Show prompt on UI thread
                this.Invoke((MethodInvoker)delegate 
                {
                    MessageBox.Show(
                        $"New version ({newVersionStr}) found!\nCurrent Version is {CurrentVersion}.\n\nDo you want to visit the download page?", 
                        "Update Available", 
                        MessageBoxButtons.YesNo, 
                        MessageBoxIcon.Information);

                    if (result == DialogResult.Yes)
                    {
                        Process.Start(bestUrl);
                    }
                });
            }
            else
            {
                // Optional: Notify user they are up to date
                this.Invoke((MethodInvoker)delegate 
                {
                    MessageBox.Show("You already have the latest version.", "Up to Date", MessageBoxButtons.OK, MessageBoxIcon.Information);
                });
            }
        }
    }
    catch (Exception ex)
    {
        Debug.WriteLine(ex.Message);
        this.Invoke((MethodInvoker)delegate 
        {
            MessageBox.Show("Unable to check for updates. Please check your internet connection.", "Update Check Failed", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        });
    }
    finally
    {
        // Re-enable the button if one was passed
        if (triggeringControl != null)
        {
            this.Invoke((MethodInvoker)delegate 
            {
                triggeringControl.Enabled = true;
            });
        }
    }

    return 0;
}
```

---

## 4. UI Implementation (The Button)
This connects the UI button to the logic.

**Action:** Double-click your "Check for Updates" button in the Designer to create the event handler, then paste this code:

```csharp
private void btnCheckUpdate_Click(object sender, EventArgs e)
{
    Control btn = sender as Control;
    if (btn != null) btn.Enabled = false; // Disable button to prevent spamming

    // Run the check in a background task so the UI doesn't freeze
    Task.Factory.StartNew(() => PerformUpdateCheck(btn));
}
```

---

## 5. Requirements for the Remote README
For this code to work, the `README.md` on your GitHub repository must follow this specific format on its **first line**:

`Your App Name v1.0.5`

*   **Your App Name**: Must match the `AppNameInReadme` constant.
*   **v1.0.5**: Must be at the very end of the line. The code looks for the last "word" in the line and attempts to parse it as a number (stripping the 'v').

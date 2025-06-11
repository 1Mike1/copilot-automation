import gitlab
import os

class GitlabClient:
    def __init__(self, url, private_token):
        self.gl = gitlab.Gitlab(url, private_token=private_token)
        self.gl.auth()

    def get_project(self, project_id):
        return self.gl.projects.get(project_id)

    def get_merge_requests(self, project_id, state='opened'):
        project = self.get_project(project_id)
        return project.mergerequests.list(state=state, all=True)

    def get_merge_request_changes(self, project_id, mr_id):
        project = self.get_project(project_id)
        mr = project.mergerequests.get(mr_id)
        return mr.changes().get('changes', [])

    def generate_prompt_for_copilot(self, project_id, mr_id, output_file=None):
        changes = self.get_merge_request_changes(project_id, mr_id)

        # Set default path if not provided
        if not output_file:
            output_dir = os.path.join("output", "prompts")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"merge_{mr_id}.py")
        else:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            for change in changes:
                f.write('"""\n')
                f.write(f"# File: {change['new_path']}\n")
                f.write("# Diff:\n")
                f.write(change['diff'] + "\n")
                f.write('"""\n\n')

            # Prompt to Copilot
            f.write("##\n")
            f.write("##")
            f.write("\n## Read the above code changes from multiple files in this request.")
            f.write("\n## Suggest a production-level optimized version of the changed code.")
            f.write("\n## PLEASE PERFORM THE CODE REVIEW AND SUGGEST THE OPTIMIZED CODE")
            f.write("\n## Copilot: MAKE TO SURE ONLY ADD SUGGESTIO FOR LINES WHERE YOUR FEEL THAT THE CODE CAN BE OPTIMIZED AND NOT THE WHOLE CODE")
            f.write("\n## Copilot: MAKE THES SUGGESTIONS FOR WILL BE GET DONE IN SINGLE GO, AT ONCE ONLY I DON'T WANT TO REPEAT THE PROMPT")
            f.write('\n## DONT WAIT FOR ME TO REPEAT THE PROMPT, JUST DO IT')
            f.write('\n## AFTER ALL THE SUGGESTION ARE DONE, PLEASE ADD THE TEST CASES FOR THE CODE CHANGES')
            f.write("\n##")
            f.write("\n## Copilot: PLEASE GIVE THE CODE AND TEST CASES IN THE FUNCTION BELOW IN SINGLE GO, AT ONCE ONLY I DON'T WANT TO REPEAT THE PROMPT") 
            f.write("\n##")
            f.write("\n")

        print(f"✅ Prompt generated at: {output_file}")


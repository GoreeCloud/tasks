// Vikunja and GoreeCloud Tasks contributors.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import "fmt"

// validateTodoistSync checks graph integrity before creating any destination
// records. Unsupported or incomplete source references must stop an import,
// never make apparently successful tasks or notes disappear.
func validateTodoistSync(data *sync) error {
	if data == nil {
		return fmt.Errorf("todoist migration: empty source snapshot")
	}

	projects := make(map[string]bool, len(data.Projects))
	for _, p := range data.Projects {
		if p == nil || p.ID == "" {
			return fmt.Errorf("todoist migration: project with missing identity")
		}
		if projects[p.ID] {
			return fmt.Errorf("todoist migration: duplicate project %s", p.ID)
		}
		projects[p.ID] = true
		if p.ParentID != "" {
			return fmt.Errorf("todoist migration: nested project %s requires hierarchy preservation before import", p.ID)
		}
	}

	sections := make(map[string]string, len(data.Sections))
	for _, section := range data.Sections {
		if section == nil || section.ID == "" {
			return fmt.Errorf("todoist migration: section with missing identity")
		}
		if section.IsDeleted {
			continue
		}
		if !projects[section.ProjectID] {
			return fmt.Errorf("todoist migration: section %s refers to missing project %s", section.ID, section.ProjectID)
		}
		if _, exists := sections[section.ID]; exists {
			return fmt.Errorf("todoist migration: duplicate section %s", section.ID)
		}
		sections[section.ID] = section.ProjectID
	}

	labels := make(map[string]bool, len(data.Labels))
	for _, label := range data.Labels {
		if label == nil || label.Name == "" {
			return fmt.Errorf("todoist migration: label with missing name")
		}
		if labels[label.Name] {
			return fmt.Errorf("todoist migration: duplicate label %s", label.Name)
		}
		labels[label.Name] = true
	}

	items := make(map[string]*item, len(data.Items))
	for _, i := range data.Items {
		if i == nil || i.ID == "" {
			return fmt.Errorf("todoist migration: task with missing identity")
		}
		if _, exists := items[i.ID]; exists {
			return fmt.Errorf("todoist migration: duplicate task %s", i.ID)
		}
		if !projects[i.ProjectID] {
			return fmt.Errorf("todoist migration: task %s refers to missing project %s", i.ID, i.ProjectID)
		}
		if i.SectionID != "" && sections[i.SectionID] != i.ProjectID {
			return fmt.Errorf("todoist migration: task %s refers to missing or foreign section %s", i.ID, i.SectionID)
		}
		if i.Due != nil && i.Due.IsRecurring && parseTodoistRepeat(i.Due) == 0 {
			return fmt.Errorf("todoist migration: task %s uses an unsupported recurring schedule", i.ID)
		}
		for _, name := range i.Labels {
			if !labels[name] {
				return fmt.Errorf("todoist migration: task %s refers to missing label %s", i.ID, name)
			}
		}
		items[i.ID] = i
	}

	for _, i := range data.Items {
		if i.ParentID == "" {
			continue
		}
		parent, found := items[i.ParentID]
		if !found {
			return fmt.Errorf("todoist migration: task %s refers to missing parent %s", i.ID, i.ParentID)
		}
		if parent.ProjectID != i.ProjectID {
			return fmt.Errorf("todoist migration: task %s has a parent in a different project", i.ID)
		}
		// Every ancestor must terminate. A cycle cannot be inserted safely.
		visited := map[string]bool{i.ID: true}
		for current := parent; current != nil; {
			if visited[current.ID] {
				return fmt.Errorf("todoist migration: cyclic subtasks involving %s", i.ID)
			}
			visited[current.ID] = true
			current = items[current.ParentID]
		}
	}

	for _, note := range data.Notes {
		if note == nil || !hasSourceTask(items, note.ItemID) {
			return fmt.Errorf("todoist migration: note refers to a missing task")
		}
	}
	for _, note := range data.ProjectNotes {
		if note == nil || !projects[note.ProjectID] {
			return fmt.Errorf("todoist migration: project note refers to a missing project")
		}
		if note.FileAttachment != nil {
			return fmt.Errorf("todoist migration: project-note attachments require a preservation strategy before import")
		}
	}
	for _, r := range data.Reminders {
		if r == nil || !hasSourceTask(items, r.ItemID) {
			return fmt.Errorf("todoist migration: reminder refers to a missing task")
		}
		if r.Due == nil {
			return fmt.Errorf("todoist migration: reminder %s lacks a due timestamp", r.ID)
		}
	}
	return nil
}

func hasSourceTask(items map[string]*item, id string) bool {
	_, found := items[id]
	return found
}

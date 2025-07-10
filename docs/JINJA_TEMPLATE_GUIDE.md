# Jinja DOCX Template Guide

## Overview

The Section E parser now supports Jinja-based DOCX templates, allowing you to create dynamic Word documents using `{{ variable.name }}` syntax. This provides more flexibility than the traditional cell-mapping approach.

## Template Variables

### Employee Information

Use these variables in your DOCX template:

```jinja
{{ employee.name }}
{{ employee.role_in_contract }}
{{ employee.years_experience.total }}
{{ employee.years_experience.with_current_firm }}
{{ employee.firm_name_and_location }}
{{ employee.education }}
{{ employee.current_professional_registration }}
{{ employee.other_professional_qualifications }}
```

### Project Information

Projects are mapped as `projectA`, `projectB`, `projectC`, `projectD`, and `projectE`:

```jinja
{{ projectA.title_and_location }}
{{ projectA.year_completed.professional_services }}
{{ projectA.year_completed.construction }}
{{ projectA.description.scope }}
{{ projectA.description.cost }}
{{ projectA.description.fee }}
{{ projectA.description.role }}

{{ projectB.title_and_location }}
{{ projectB.year_completed.professional_services }}
{{ projectB.year_completed.construction }}
{{ projectB.description.scope }}
{{ projectB.description.cost }}
{{ projectB.description.fee }}
{{ projectB.description.role }}

<!-- Continue with projectC, projectD, projectE as needed -->
```

## Case Insensitivity

The system handles case variations automatically. These are all equivalent:

- `{{ employee.name }}`
- `{{ EMPLOYEE.NAME }}`
- `{{ Employee.Name }}`

## Template Setup

1. **Create Template**: Create a DOCX file with Jinja variables where you want data to appear
2. **Save as JinjaTemplate.docx**: Place the file in the `templates/` directory
3. **Install Dependencies**: Run `pip install docxtpl Jinja2`

## Example Template Structure

```
Section E Resume

Name: {{ employee.name }}
Role: {{ employee.role_in_contract }}
Total Experience: {{ employee.years_experience.total }} years
Firm Experience: {{ employee.years_experience.with_current_firm }} years

Firm: {{ employee.firm_name_and_location }}

Education: {{ employee.education }}

Registration: {{ employee.current_professional_registration }}

Qualifications: {{ employee.other_professional_qualifications }}

Project 1: {{ projectA.title_and_location }}
Year: {{ projectA.year_completed.professional_services }}
Scope: {{ projectA.description.scope }}
Role: {{ projectA.description.role }}

Project 2: {{ projectB.title_and_location }}
Year: {{ projectB.year_completed.professional_services }}
Scope: {{ projectB.description.scope }}
Role: {{ projectB.description.role }}
```

## Using in the UI

1. Open the Section E Resume modal
2. Fill in employee and project information
3. In the Template Selection section, choose **"Jinja Template (Dynamic Content)"**
4. Click **Generate Section E Resume**
5. The system will generate a DOCX file with your data filled in

## Testing

Run the test suite to validate your setup:

```bash
python tests/test_jinja_docx_generator.py
```

## Troubleshooting

### Common Issues

1. **Import Error**: Install dependencies with `pip install docxtpl Jinja2`
2. **Template Not Found**: Ensure `JinjaTemplate.docx` is in the `templates/` folder
3. **Variables Not Rendering**: Check that variable names match exactly (case doesn't matter)
4. **Empty Fields**: Empty fields will display as blank in the generated document

### Debug Mode

To see what data is being passed to the template, check the console output when generating a resume. The system will log:

- Template data preparation
- Number of projects mapped
- Generation success/failure

## Advanced Features

### Conditional Content

You can use Jinja conditionals for optional content:

```jinja
{% if employee.current_professional_registration %}
Registration: {{ employee.current_professional_registration }}
{% endif %}
```

### Loops for Projects

For dynamic project lists, use the `projects` array:

```jinja
{% for project in projects %}
    {% if project.title_and_location %}
Project: {{ project.title_and_location }}
Year: {{ project.year_completed.professional_services }}
Scope: {{ project.description.scope }}
Role: {{ project.description.role }}
    {% endif %}
{% endfor %}
```

Or access individual projects directly:

```jinja
{% if projectA.title_and_location %}
Project A: {{ projectA.title_and_location }}
{% endif %}
{% if projectB.title_and_location %}
Project B: {{ projectB.title_and_location }}
{% endif %}
```

## Benefits vs. Cell Mapping

| Feature | Jinja Templates | Cell Mapping |
|---------|----------------|--------------|
| Flexibility | High - place variables anywhere | Limited - specific cells only |
| Layout Control | Full control | Fixed table structure |
| Conditional Content | Yes | No |
| Learning Curve | Moderate | Low |
| Template Creation | Any Word editor | Requires specific table format | 
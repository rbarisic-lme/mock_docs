# Template-Specific Images Directory

This directory contains template-specific images that can be used to replace default template images based on the `images` configuration in template*keys*\*.json files.

## How it works:

1. **Default images** are stored in `input_img/` and used for template creation
2. **Template-specific replacements** are stored here in `config_img/`
3. **Image replacement mapping** is defined in the `images` section of template*keys*\*.json files

## Example Configuration:

In template_keys_010.json:

```json
{
  "images": {
    "demo-insurance.jpg": "demo-insurance_novaschutz.jpg",
    "demo-broker.jpg": "demo-broker.jpg",
    "demo-company-logo.jpg": "demo-company-logo.jpg"
  }
}
```

This means:

- When the template references `demo-insurance.jpg`, it will use `demo-insurance_novaschutz.jpg` from this folder
- When the template references `demo-broker.jpg`, it will use `demo-broker.jpg` from this folder
- etc.

## Business Value:

- **Multi-tenant support**: Different clients can have their own branded images
- **Template customization**: Same template structure with client-specific assets
- **Brand consistency**: Each client gets their own logos, letterheads, signatures
- **Scalable solution**: Easy to add new clients without changing template logic

## File Naming Convention:

- `{base_name}_{variant}.{extension}`
- Example: `demo-insurance_novaschutz.jpg`, `demo-insurance_securelife.jpg`

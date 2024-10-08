# zen - A Python Library for Interacting with Zenodo

<img src="docs/_images/zen-logo.png" alt="zen icon" align="right" height="80" />

## Overview 

**zen** is a Python library that provides a simple and intuitive way to interact with 
[Zenodo](https://zenodo.org), a popular research data repository. With **zen**, you can automate 
and streamline various tasks related to creating, managing, and exploring Zenodo depositions, 
all within your Python environment.

## Features

- **Deposition Management**: Easily create, retrieve, update, and delete Zenodo depositions from 
your Python code.

- **Local File Management**: Handle local files and datasets, with built-in support for templating.

- **File Handling**: Upload, download, and manage files associated with your Zenodo depositions.

- **Deposition Listings**: Retrieve a list of depositions from your Zenodo account with various 
filtering options.

- **Integrity Checking**: Automatically calculate checksums for files within your depositions for 
integrity checking.

- **Interactivity with Zenodo API**: Communicate with the Zenodo API seamlessly to access and 
manipulate your deposition data.

## Installation

You can install **zen** using pip:

```bash
pip install -e 'git+https://github.com/Open-Earth-Monitor/zen#egg=zen'
```

## Getting Started
Using **zen** in your Python project is straightforward. Here's a quick example of how to create a 
new Zenodo deposition:

```python
from zen import Zenodo

# Initialize Zenodo with your API token
zen = Zenodo(url=Zenodo.sandbox_url, token="your_api_token")

# Create a deposition
dep = zen.depositions.create()

# Uploading a file
dep.files.create('examples/file1.csv')

# Print the deposition ID
print(f"Deposition ID: {dep.id}")

```

### Managing local files
To associate a set of files to a Zenodo deposition, you can set up a local dataset. With a local
dataset, users can easily track local changes and manage big datasets uploading. If the local
files are stored in a remote machine, **zen** will download them temporarily just before the
uploading.

```python
from zen import LocalFiles, Zenodo

# Create a dataset
ds = LocalFiles(['examples/file1.csv', 'examples/file2.csv'], dataset_path='examples/dataset.json')

# Initialize Zenodo with your API token
zen = Zenodo(url=Zenodo.sandbox_url, token="your_api_token")

# Create a deposition if there is no one already defined
ds.set_deposition(api=zen, create_if_not_exists=True)

# Save and Load a saved dataset
ds.save()
ds = LocalFiles.from_file('examples/dataset.json')

# Retrieve the deposition
ds.set_deposition(api=zen)

# Upload files to Zenodo
ds.upload()

# Add more files to local dataset
ds.add(['examples/file3.csv'])
ds.save()

# Just upload modified or new files to Zenodo
ds.upload()

```

### Managing metadata
Metadata management is easy with **zen**. The package provides helper classes to fill metadata
information and document all Zenodo metadata tags. **zen** also supports basic templating 
that enables users to automate and personalize dataset descriptions using templated metadata.

```python

# Create a metadata for a dataset
dep.metadata.title = 'My title'
dep.metadata.description = 'My description of files from {index_min} to {index_max}.'

# Add a creator
dep.metadata.creators.clear()
dep.metadata.creators.add('My Name')

# Update metadata on Zenodo
# Create replacement value for the metadata placeholders
replacements = {'index_min': 1, 'index_max': 3}
dep.update(replacements=replacements)


```

The `replacements` dictionary used to render the metadata could get that information from 
the local dataset itself. One way to do this is to extract that information from the 
filenames. Users can do this in two different ways, (1) by providing a filename template 
that will be used to parse filenames and information will be stored in file properties;
or (2) by generating the filenames using that template filename.

1) Providing a filename template

In this example, file properties will be extracted from filenames using the placeholder as
a pattern.

```python

# Create a template with 'index' placeholder
filename_template = 'file{index}.csv'
ds = LocalFiles(['examples/file1.csv', 'examples/file2.csv', 'examples/file3.csv'], 
                 template=filename_template, dataset_path='examples/dataset.json')

print(ds.summary())
#... {'index_min': '1', 'index_max': '3'}

# Get the previous metadata template and render a metadata
replacements = ds.summary()
dep.update(replacements=replacements)

```

2) Generating local files' filenames

In this example, file properties will be generated along with filenames by calling `expand()` 
method. Multiple calls on this method will generate filenames by combining all occurrences in 
a cartesian product.

```python

# Create a template with 'index' placeholder
filename_template = 'file{index}.csv'
ds = LocalFiles.from_template(filename_template)

# Expand the index placeholder
ds.expand(index=[1,2,3])
ds.modify_url(prefix='examples/')

print([f.url for f in ds])
#... ['examples/file1.csv', 'examples/file2.csv', 'examples/file3.csv']

# Get the previous metadata template and render a metadata
replacements = ds.summary()
dep.update(replacements=replacements)

```

## Documentation
For detailed usage and additional examples, please refer to the zen 
[documentation](https://open-earth-monitor.github.io/zen).

## Contributing
We welcome contributions! If you would like to contribute to the zen library, please see our [Contributing Guide](CONTRIBUTING.md) for more information.

## License
© OpenGeoHub Foundation, 2023-2024. Licensed under the [MIT License](LICENSE).

## Acknowledgements & Funding
This work is supported by [OpenGeoHub Foundation](https://opengeohub.org/) and has received 
funding from the European Commission (EC) through the projects:

- [Open-Earth-Monitor Cyberinfrastructure](https://earthmonitor.org/): Environmental information 
  to support EU’s Green Deal (1 Jun. 2022 – 31 May 2026 - 
  [101059548](https://cordis.europa.eu/project/id/101059548))
- [AI4SoilHealth](https://ai4soilhealth.eu/): Accelerating collection and use of soil health 
  information using AI technology to support the Soil Deal for Europe and EU Soil Observatory 
  (1 Jan. 2023 – 31 Dec. 2026 - [101086179](https://cordis.europa.eu/project/id/101086179))

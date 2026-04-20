Installation
============

Recommended installation (system tool)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest and recommended way to install **SeisCat** is as a system tool
using the official installation script. This installs SeisCat independently of
your system Python (if any) and manages it via
`uv <https://docs.astral.sh/uv/>`_.

Linux & macOS
~~~~~~~~~~~~~

Run one of the following commands:

.. code-block:: sh

   sh -c "$(curl -fsSL https://raw.githubusercontent.com/SeismicSource/seiscat/refs/heads/main/scripts/install_seiscat_uv.sh)"

or:

.. code-block:: sh

   sh -c "$(wget https://raw.githubusercontent.com/SeismicSource/seiscat/refs/heads/main/scripts/install_seiscat_uv.sh -O -)"

Windows (PowerShell)
~~~~~~~~~~~~~~~~~~~~

Run the following command in PowerShell:

.. code-block:: powershell

   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/SeismicSource/seiscat/refs/heads/main/scripts/install_seiscat_uv.ps1 | iex"

Updating SeisCat
^^^^^^^^^^^^^^^^

Once installed as a system tool, SeisCat can be updated directly:

.. code-block:: sh

   seiscat self update

To switch to the development version:

.. code-block:: sh

   seiscat self update --git

Alternative installation methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using pip (PyPI)
~~~~~~~~~~~~~~~~

The latest stable release is available on the Python Package Index:

.. code-block:: sh

   pip install seiscat

Optional plotting backends:

.. code-block:: sh

   pip install seiscat[cartopy]
   pip install seiscat[plotly]
   pip install seiscat[folium]
   pip install seiscat[cartopy,plotly,folium]

To upgrade:

.. code-block:: sh

   pip install --upgrade seiscat

Installing a development snapshot (pip + git)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install the latest development version:

.. code-block:: sh

   pip install git+https://github.com/SeismicSource/seiscat.git

From GitHub releases
~~~~~~~~~~~~~~~~~~~~

Download a release archive from the SeisCat releases page:
https://github.com/SeismicSource/seiscat/releases

Then install it directly:

.. code-block:: sh

   pip install seiscat-X.Y.zip

or:

.. code-block:: sh

   pip install seiscat-X.Y.tar.gz

Working from source (editable install)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository:

.. code-block:: sh

   git clone https://github.com/SeismicSource/seiscat.git

or via SSH:

.. code-block:: sh

   git clone git@github.com:SeismicSource/seiscat.git

Then install in editable mode:

.. code-block:: sh

   pip install -e .

Optional extras:

.. code-block:: sh

   pip install -e .[cartopy]
   pip install -e .[plotly]
   pip install -e .[folium]
   pip install -e .[cartopy,plotly,folium]

To update:

.. code-block:: sh

   git pull

With editable installs, changes are reflected immediately without reinstalling.

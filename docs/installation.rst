Installation
============

Installing the latest release
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using pip and PyPI (preferred method)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The latest release of SeisCat is available on the
`Python Package Index <https://pypi.org/project/seiscat/>`_.

You can install it easily through ``pip``\ :

.. code-block::

   pip install seiscat


To upgrade from a previously installed version:

.. code-block::

   pip install --upgrade seiscat


From SeisCat GitHub releases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the latest release from the
`releases page <https://github.com/SeismicSource/seiscat/releases>`_\ ,
in ``zip`` or ``tar.gz`` format, then:

.. code-block::

   pip install seiscat-X.Y.zip


or

.. code-block::

   pip install seiscat-X.Y.tar.gz


Where, ``X.Y`` is the version number (e.g., ``0.1``\ ).
You don't need to uncompress the release files yourself.

Installing a developer snapshot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need a recent feature that is not in the latest release (see the
``unreleased`` section in :ref:`changelog`), you want to use the
more recent development snapshot from the
`SeisCat GitHub repository <https://github.com/SeismicSource/seiscat>`_.

Using pip (preferred method)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to install the most recent development snapshot is to download
and install it through ``pip``\ , using its builtin ``git`` client:

.. code-block::

   pip install git+https://github.com/SeismicSource/seiscat.git


Run this command again, from times to times, to keep SeisCat updated with
the development version.

Cloning the SeisCat GitHub repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to take a look at the source code (and possibly modify it 😉),
clone the project using ``git``\ :

.. code-block::

   git clone https://github.com/SeismicSource/seiscat.git


or, using SSH:

.. code-block::

   git clone git@github.com:SeismicSource/seiscat.git


(avoid using the "Download ZIP" option from the green "Code" button, since
version number is lost).

Then, go into the ``seiscat`` main directory and install the code in "editable
mode" by running:

.. code-block::

   pip install -e .


You can keep your local SeisCat repository updated by running ``git pull``
from times to times. Thanks to ``pip``\ 's "editable mode", you don't need to
reinstall SeisCat after each update.

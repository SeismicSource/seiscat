Getting Started
===============

To get help:

.. code-block::

   seiscat -h


First thing to do is to generate a sample configuration file:

.. code-block::

   seiscat sampleconfig


Then, edit the configuration file and init the database:

.. code-block::

   seiscat initdb


Alternatively, you can init the database from a CSV file:

.. code-block::

    seiscat initdb -f /path/to/your/catalog.csv

To update an existing database from an FDSN webservice, run:

.. code-block::

   seiscat updatedb


(This will use the configuration parameter ``recheck_period`` to recheck the
last *n* days or hours).

Alternatively, you can update the database from a CSV file:

.. code-block::

    seiscat updatedb -f /path/to/your/catalog.csv


You can edit the attributes of specific events in the database using:

.. code-block::

    seiscat editdb


You can print the catalog to screen:

.. code-block::

   seiscat print


Or plot it:

.. code-block::

   seiscat plot


Each of the above commands can have its own options.
As an example, to discover the options for the ``plot`` command, try:

.. code-block::

    seiscat plot -h


SeisCat supports command line tab completion for arguments, thanks to
`argcomplete <https://kislyuk.github.io/argcomplete/>`__.
To enable command line tab completion run:

.. code-block::

    activate-global-python-argcomplete

(This is a one-time command that needs to be run only once).

Or, alternatively, add the following line to your ``.bashrc`` or ``.zshrc``:

.. code-block::

   eval "$(register-python-argcomplete seiscat)"
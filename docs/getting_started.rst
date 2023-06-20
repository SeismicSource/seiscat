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


To keep the database updated, run on a regular basis:

.. code-block::

   seiscat updatedb


(This will use the configuration parameter ``recheck_period`` to recheck the
last *n* days or hours).

You can print the catalog to screen:

.. code-block::

   seiscat print


Or plot it:

.. code-block::

   seiscat plot


SeisCat supports command line tab completion for arguments, thanks to
`argcomplete <https://kislyuk.github.io/argcomplete/>`__. To enable
command line tab completion, add the following line to your ``.bashrc``
or ``.zshrc``:

.. code-block::

   eval "$(register-python-argcomplete seiscat)"
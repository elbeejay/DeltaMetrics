import abc

import numpy as np
from scipy import stats, sparse

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from . import cube
from . import plot


class BaseSectionVariable(np.ndarray):
    """Section variable.

    We subclass the numpy `ndarray`, in order to have `ndarray` methods to
    the object in subclasses (e.g., `add`, slicing).

    This is a really lightweight subclass of the `np.ndarray`, but it allows
    us to add coordinate arrays to the variable, which are always needed to
    display info correctly. We also gain the ability to return the correct
    subclass type following views and slicing of the subclasses.

    .. note::

        Subclasses should implement the ``__init__`` method.

    """
    _spacetime_names = ['full', 'spacetime', 'as spacetime', 'as_spacetime']
    _preserved_names = ['psvd', 'preserved', 'as preserved', 'as_preserved']
    _stratigraphy_names = ['strat', 'strata',
                           'stratigraphy', 'as stratigraphy', 'as_stratigraphy']

    def __new__(cls, _data, _s, _z, _psvd_mask=None, **unused_kwargs):
        # Input array is an already formed ndarray instance
        obj = np.asarray(_data).view(cls)
        obj._psvd_mask = _psvd_mask
        obj._s = _s
        obj._z = _z
        obj._S, obj._Z = np.meshgrid(obj._s, obj._z)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self._psvd_mask = getattr(obj, '_psvd_mask', None)
        self._s = getattr(obj, '_s', None)
        self._z = getattr(obj, '_z', None)
        self._S, self._Z = np.meshgrid(self._s, self._z)

    @abc.abstractmethod
    def get_display_arrays(self):
        """get_display_arrays."""
        ...

    @abc.abstractmethod
    def get_display_lines(self):
        """get_display_lines."""
        ...

    @abc.abstractmethod
    def get_display_limits(self):
        """get_display_limits."""
        ...


class DataSectionVariable(BaseSectionVariable):
    """Variable returned from a DataCube Section.

    Subclasses numpy MaskedArray, so supports arbitrary math.

    """
    _default_style = 'spacetime'

    def __init__(self, _data, _s, _z, _psvd_mask=None, _strat_attr=None):
        """Construct the array from section info.

        Parameters
        ----------
        _data : :obj:`ndarray`
            Slice of underlying data. Generated by slicing the CubeVariable
            with: :code:`cube[var][:, self._y, self._x]`

        _psvd_mask : :obj:`ndarray`
            Mask indicating the *preserved* voxels. Must have same shape as
            `_data`.

        strat_attr : :obj:`dict`
            Dictionary of attributes regarding stratigraphy generated by the
            section, on instantiation. May be a nearly empty dictionary, but
            must always be provided. Only used if
            `Section._knows_stratigraphy`.

        .. note::
            ``__new__`` from the base class is called *before* ``__init__``.
            The ``__new__`` method configures the `_data`, `_s`, `_z`, and
            `_psvd_mask` arguments.
        """
        if not (_strat_attr is None):
            self.strat_attr = _strat_attr
            self._knows_stratigraphy = True
        else:
            self._knows_stratigraphy = False

    @property
    def knows_stratigraphy(self):
        """Whether the data variable knows preservation information."""
        return self._knows_stratigraphy

    def _check_knows_stratigraphy(self):
        """Check whether "knows_stratigraphy".

        Raises
        ------
        AttributeError
            Raises if does not know stratigraphy.
        """
        if not self._knows_stratigraphy:
            raise AttributeError('No preservation information.')
        return self._knows_stratigraphy

    def as_preserved(self):
        """Variable with only preserved values.

        Returns
        -------
        ma : :obj:`np.ma.MaskedArray`
            A numpy MaskedArray with non-preserved values masked.
        """
        if self._check_knows_stratigraphy():
            return np.ma.MaskedArray(self, ~self._psvd_mask)

    def as_stratigraphy(self):
        """Variable as preserved stratigraphy.

        .. warning::

            This method returns a sparse array that is not suitable to be
            displayed directly. Use
            :obj:`get_display_arrays(style='stratigraphy')` instead to get
            corresponding x-y coordinates for plotting the array.
        """
        if self._check_knows_stratigraphy():
            # actual data, where preserved
            _psvd_data = self[self.strat_attr['psvd_idx']]
            _sp = sparse.coo_matrix((_psvd_data,
                                     (self.strat_attr['z_sp'],
                                      self.strat_attr['s_sp'])))
            return _sp

    def get_display_arrays(self, style=None):
        """Get arrays for display as meshes, or images.

        Parameters
        ----------

        """
        style = self._default_style if (style is None) else style
        if style in self._spacetime_names:
            return self, self._S, self._Z
        elif style in self._preserved_names:
            return self.as_preserved(), self._S, self._Z
        elif style in self._stratigraphy_names:
            _sp = self.as_stratigraphy()
            _arr_Y = self.strat_attr['psvd_flld'][:_sp.shape[0], ...]
            _arr_X = np.tile(self._s, (_sp.shape[0], 1))
            return _sp.toarray().view(DataSectionVariable), _arr_X, _arr_Y
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))

    def get_display_lines(self, style=None):
        """
        """
        def _reshape_long(X):
            # util for reshaping x- and y-values appropriately
            return np.vstack((X[:, :-1].flatten(), X[:, 1:].flatten())).T.reshape(-1, 2, 1)

        style = self._default_style if (style is None) else style
        if style in self._spacetime_names:
            y = _reshape_long(self._Z)
            data = self[:, :-1]
        elif style in self._preserved_names:
            if self._check_knows_stratigraphy():
                y = _reshape_long(self._Z)
                data = self.as_preserved()[:, :-1]
        elif style in self._stratigraphy_names:
            if self._check_knows_stratigraphy():
                y = _reshape_long(np.copy(self.strat_attr['strata']))
                data = self[:, :-1]
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))

        x = _reshape_long(self._S)
        segments = np.concatenate([x, y], axis=2)
        return data, segments

    def get_display_limits(self, style=None):
        """
        """
        style = self._default_style if (style is None) else style
        if (style in self._spacetime_names) or (style in self._preserved_names):
            return np.min(self._S), np.max(self._S), np.min(self._Z), np.max(self._Z)
        elif style in self._stratigraphy_names:
            if self._check_knows_stratigraphy():
                _strata = np.copy(self.strat_attr['strata'])
                return np.min(self._S), np.max(self._S), np.min(_strata), np.max(_strata) * 1.5
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))


class StratigraphySectionVariable(BaseSectionVariable):
    """
    """
    _default_style = 'stratigraphy'

    def __init__(self, _data, _s, _z):
        pass

    def _check_knows_spacetime(self):
        """Check whether "knows_spacetime".

        Raises
        ------
        AttributeError
            Raises always when this method is called, because a
            StratigraphySectionVariable will never know spacetime information
            directly.
        """
        raise AttributeError(
            'No "spacetime" or "preserved" information available.')

    def get_display_arrays(self, style=None):
        """
        """
        style = self._default_style if (style is None) else style
        if style in self._spacetime_names:
            self._check_knows_spacetime()
        elif style in self._preserved_names:
            self._check_knows_spacetime()
        elif style in self._stratigraphy_names:
            return self, self._S, self._Z
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))

    def get_display_lines(self, style=None):
        """
        """
        style = self._default_style if (style is None) else style
        if style in self._spacetime_names:
            self._check_knows_spacetime()
        elif style in self._preserved_names:
            self._check_knows_spacetime()
        elif style in self._stratigraphy_names:
            raise NotImplementedError
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))

        # return self.display_lines

    def get_display_limits(self, style=None):
        """
        """
        style = self._default_style if (style is None) else style
        if style in self._spacetime_names:
            self._check_knows_spacetime()
        elif style in self._preserved_names:
            self._check_knows_spacetime()
        elif style in self._stratigraphy_names:
            return np.min(self._S), np.max(self._S), np.min(self._Z), np.max(self._Z) * 1.5
        else:
            raise ValueError('Bad "style" argument: %s' % str(style))


class BaseSection(abc.ABC):
    """Base section object.

    Defines common attributes and methods of a section object.

    This object should wrap around many of the functions available from
    :obj:`~deltametrics.strat`.

    """

    def __init__(self, *args):
        """
        Identify coordinates defining the section.

        Parameters
        ----------
        CubeInstance : :obj:`~deltametrics.cube.Cube` subclass instance, optional
            Connect to this cube. No connection is made if cube is not provided.

        Notes
        -----

        If no arguments are passed, an empty section not connected to any cube
        is returned. This cube will will need to be manually connected to have
        any functionality (via the :meth:`connect` method.
        """
        # begin unconnected
        self._s = None
        self._z = None
        self._x = None
        self._y = None
        self._variables = None
        self.cube = None

        if len(args) > 1:
            raise ValueError('Expected single argument to %s instantiation.'
                             % type(self))

        if len(args) > 0:
            self.connect(args[0])
        else:
            pass

    def connect(self, CubeInstance):
        """Connect this Section instance to a Cube instance.
        """
        if not issubclass(type(CubeInstance), cube.BaseCube):
            raise TypeError('Expected type is subclass of {_exptype}, '
                            'but received was {_gottype}.'.format(
                                _exptype=type(cube.BaseCube),
                                _gottype=type(CubeInstance)))
        self.cube = CubeInstance
        self._variables = self.cube.variables
        self._compute_section_coords()
        self._compute_section_attrs()

    @abc.abstractmethod
    def _compute_section_coords(self):
        """Should calculate x-y coordinates of the section.

        Sets the value ``self._x`` and ``self._y`` according to the algorithm
        of each section initialization.

        .. warning::

            When implementing new section types, be sure that ``self._x`` and
            ``self._y`` are *one-dimensional arrays*, or you will get an
            improperly shaped Section array in return.
        """
        ...

    def _compute_section_attrs(self):
        """Compute attrs

        Compute the along-section coordinate array from x-y pts pairs
        definining the section.
        """
        self._s = np.cumsum(np.hstack((0, np.sqrt((self._x[1:] - self._x[:-1])**2
                                                  + (self._y[1:] - self._y[:-1])**2))))
        self._z = self.cube.z

    @property
    def trace(self):
        """Coordinates of the section in the x-y plane.
        """
        return np.column_stack((self._x, self._y))

    @property
    def s(self):
        """Along-section coordinate."""
        return self._s

    @property
    def z(self):
        """Up-section (vertical) coordinate."""
        return self._z

    @property
    def variables(self):
        """List of variables.
        """
        return self._variables

    def __getitem__(self, var):
        """Get a slice of the section.

        Slicing the section instance creates a
        :obj:`~deltametrics.section.SectionVariable` instance from data for
        variable ``var``.

        .. note:: We only support slicing by string.

        Parameters
        ----------
        var : :obj:`str`
            Which variable to slice.

        Returns
        -------
        SectionVariable : :obj:`~deltametrics.section.SectionVariable` instance
            SectionVariable instance for variable ``var``.
        """
        if type(self.cube) is cube.DataCube:
            if self.cube._knows_stratigraphy:
                return DataSectionVariable(_data=self.cube[var][:, self._y, self._x],
                                           _s=self.s, _z=self.z,
                                           _psvd_mask=self.cube.strat_attr.psvd_idx[
                                               :, self._y, self._x],
                                           _strat_attr=self.cube.strat_attr('section', self._y, self._x))
            else:
                return DataSectionVariable(_data=self.cube[var][:, self._y, self._x],
                                           _s=self.s, _z=self.z)
        elif type(self.cube) is cube.StratigraphyCube:
            return StratigraphySectionVariable(_data=self.cube[var][:, self._y, self._x],
                                               _s=self.s, _z=self.z)
        elif self.cube is None:
            raise AttributeError(
                'No cube connected. Are you sure you ran `.connect()`?')
        else:
            raise TypeError('Unknown Cube type encountered: %s'
                            % type(self.cube))

    def show(self, SectionAttribute, style='shaded', display_array_style=None,
             label=False, ax=None):
        """Show the section.

        Method enumerates convenient routines for visualizing sections of data
        and stratigraphy. Includes support for multiple data `style` and
        mutuple `display_array_style` choices as well.

        .. note::

            The colors for `style='lines'` are determined from the left-end
            edge node, and colors for the `style='shaded'` mesh are determined
            from the lower-left-end edge node of the quad.

        Parameters
        ----------

        SectionAttribute : :obj:`str`
            Which attribute to show.

        style : :obj:`str`, optional
            What style to display the section with. Choices are 'mesh' or 'line'.

        display_array_style : :obj:`str`, optional
            Argument passed to
            :obj:`~deltametrics.section.DataSectionVariable.get_display_arrays`
            or :obj:`~deltametrics.section.DataSectionVariable.get_display_lines`.
            Supported options are `'spacetime'`, `'preserved'`, and
            `'stratigraphy'`. Default is to display full spacetime plot for
            section generated from a `DataCube`, and stratigraphy for
            a `StratigraphyCube` section.

        label : :obj:`bool`, `str`, optional
            Display a label of the variable name on the plot. Default is
            False, display nothing. If ``label=True``, the label name from the
            :obj:`~deltametrics.plot.VariableSet` is used. Other arguments are
            attempted to coerce to `str`, and the literal is diplayed.

        Examples
        --------
        *Example 1:* Display the `velocity` spacetime section of a DataCube.

        .. doctest::

            >>> rcm8cube = dm.sample_data.cube.rcm8()
            >>> rcm8cube.register_section('demo', dm.section.StrikeSection(y=5))
            >>> rcm8cube.sections['demo'].show('velocity')

        .. plot:: section/section_demo_spacetime.py

        Note that the last line above is functionally equivalent to
        ``rcm8cube.show_section('demo', 'velocity')``.

        *Example 2:* Display a section, with "quick" stratigraphy, as the
        `depth` attribute, displaying several different section styles.

        .. doctest::

            >>> rcm8cube = dm.sample_data.cube.rcm8()
            >>> rcm8cube.stratigraphy_from('eta')
            >>> rcm8cube.register_section('demo', dm.section.StrikeSection(y=5))

            >>> fig, ax = plt.subplots(4, 1, sharex=True, figsize=(6, 9))
            >>> rcm8cube.sections['demo'].show('depth', display_array_style='spacetime',
            ...                                 ax=ax[0], label='spacetime')
            >>> rcm8cube.sections['demo'].show('depth', display_array_style='preserved',
            ...                                ax=ax[1], label='preserved')
            >>> rcm8cube.sections['demo'].show('depth', display_array_style='stratigraphy',
            ...                                ax=ax[2], label='quick stratigraphy')
            >>> rcm8cube.sections['demo'].show('depth', style='lines', display_array_style='stratigraphy',
            ...                                ax=ax[3], label='quick stratigraphy')

        .. plot:: section/section_demo_quick_strat.py
        """
        # process arguments and inputs
        if not ax:
            ax = plt.gca()
        _varinfo = self.cube.varset[SectionAttribute] if \
            issubclass(type(self.cube), cube.BaseCube) else plot.VariableSet()[SectionAttribute]
        SectionVariableInstance = self[SectionAttribute]

        # main routines for plot styles
        if style in ['shade', 'shaded']:
            _data, _X, _Y = SectionVariableInstance.get_display_arrays(
                style=display_array_style)
            pcm = ax.pcolormesh(_X, _Y, _data, cmap=_varinfo.cmap, norm=_varinfo.norm,
                                vmin=_varinfo.vmin, vmax=_varinfo.vmax,
                                rasterized=True, shading='auto')
            cb = plot.append_colorbar(pcm, ax)
        elif style in ['line', 'lines']:
            _data, _segments = SectionVariableInstance.get_display_lines(
                style=display_array_style)
            if display_array_style in SectionVariableInstance._stratigraphy_names:
                # flip = draw late to early
                _data = np.fliplr(np.flipud(_data))
                _segments = np.flipud(_segments)
            lc = LineCollection(_segments, cmap=_varinfo.cmap)
            lc.set_array(_data.flatten())
            lc.set_linewidth(1.25)
            line = ax.add_collection(lc)
            cb = plot.append_colorbar(line, ax)
        else:
            raise ValueError('Bad style argument: "%s"' % style)

        # style adjustments
        if label:
            _label = _varinfo.label if (label is True) else str(
                label)  # use custom if passed
            ax.text(0.99, 0.8, _label, fontsize=8,
                    horizontalalignment='right', verticalalignment='center',
                    transform=ax.transAxes)
        xmin, xmax, ymin, ymax = SectionVariableInstance.get_display_limits(
            style=display_array_style)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)


class PathSection(BaseSection):
    """Path section object.

    Create a Section along user-specified path.

    .. note::

        Currently, this extracts only *at* the points specified. A good
        improvement would be to interpolate along the path defined, and
        extract the section everywhere the path intersects within 50% of the
        center of the surface area of a grid cell.
    """

    def __init__(self, *args, path):
        """Instantiate.

        Parameters
        ----------
        path : :obj:`ndarray`
            An Mx2 `ndarray` specifying the x-y pairs of coordinates to
            extract the section from.

        Notes
        -----

        `path` must be supplied as a keyword argument.

        """
        self._path = path

        super().__init__(*args)

    def _compute_section_coords(self):
        """Calculate coordinates of the strike section.
        """
        self._x = self._path[:, 1]
        self._y = self._path[:, 0]

    @property
    def path(self):
        """Path of the PathSection.

        Returns same as `trace` property.
        """
        return self._trace


class StrikeSection(BaseSection):
    """Strike section object.
    """

    def __init__(self, *args, y=0):

        self.y = y  # strike coord scalar
        super().__init__(*args)

    def _compute_section_coords(self):
        """Calculate coordinates of the strike section.
        """
        _nx = self.cube['eta'].shape[2]
        self._x = np.arange(_nx)
        self._y = np.tile(self.y, (_nx))


class DipSection(BaseSection):
    """Dip section object.

    """

    def __init__(self, x=-1):
        raise NotImplementedError
        # choose center point if x=-1


class RadialSection(BaseSection):
    """Radial section object.

    """

    def __init__(self, apex, radius):
        raise NotImplementedError

from napari import Viewer
from napari.layers import Layer


from vispy.scene.visuals import Text
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from napari._vispy.utils.visual import overlay_to_visual
from napari.components.overlays import CanvasOverlay


# the overlay model should inherit from either CanvasOverlay or SceneOverlay
# depending on whether it needs to live in "screen space" or "scene space"
# (i.e: if it should be affected by camera, dims, ndisplay, ...)
class OrientationOverlay(CanvasOverlay):
    """Orientation marker at one of the cardinal directions of the canvas."""
    text: str
    size: int = 10

# the vispy overlay class should handle connecting the model to the vispy
# visual we use the ViewerOverlayMixin because this overlay is attached to the
# viewer, and not a specific layer
class VispyOrientationOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Orientation marker at one of the cardinal directions of the canvas."""
    # all arguments are keyword-only. viewer, overlay and parent should always
    # be present.
    def __init__(self, **kwargs):
        # the node argument for the base class is the vispy visual
        super().__init__(
            node=Text(text='', bold=True, color='white', font_size=10),
            **kwargs
        )
        # we need to connect events from the model to callbacks that update
        # the visual
        self.overlay.events.text.connect(self._on_text_change)
        self.overlay.events.size.connect(self._on_size_change)

        # we *don't* need to connect position, because that's done for us in
        # the base classes of CanvasOverlay. We *can* overload
        # `_on_position_change` if we want to do some extra work.
        # `self.x_offset` and `self.y_offset` can be set in the overload to
        # nudge the canvas overlay around.

        # at the end of the init of subclasses of VispyBaseOverlay we always
        # need to call reset to initialize properly
        self.reset()

    def _on_text_change(self, event=None):
        self.node.text = self.overlay.text
        # trigger position update since the overall size of the visual *may*
        # change if the text changes
        self._on_position_change()

    def _on_size_change(self, event=None):
        self.node.font_size = self.overlay.size
        # trigger position update since the size changed
        self._on_position_change()

    # always add all new callbacks to the reset() method
    def reset(self):
        super().reset()
        self._on_text_change()
        self._on_size_change()


# for napari to know how to use this overlay, we need to add it to the
# overlay_to_visual dict. This will ideally be in a public API at some point
overlay_to_visual[OrientationOverlay] = VispyOrientationOverlay


def add_orientation_markers(viewer: Viewer, layer: Layer):

    print('imma add it!')
    layer_ome_meta = layer.metadata.get('napari-ome-zarr', None)
    if layer_ome_meta is None:
        import warnings
        warnings.warn('Selected layer has no orientation metadata.')
        return

    if viewer.dims.ndisplay == 3:
        warnings.warn('Orientation markers are not supported in 3D.')
        return

    axes_displayed = [
        viewer.dims.axis_labels[i] for i in viewer.dims.displayed
    ]

    axes_meta = layer_ome_meta['multiscales'][0]['axes']
    # TODO: they may not match as of napari 0.9.0, so check that list is not
    #       empty
    vertical_axis = [
        ax for ax in axes_meta if ax['name'] == axes_displayed[0]
    ][0]
    horizontal_axis = [
        ax for ax in axes_meta if ax['name'] == axes_displayed[1]
    ][0]

    if (ori := vertical_axis['orientation']) is not None:
        ori_labels = [v[0].upper() for v in ori['value'].split('-to-')]
        if viewer.scene.camera.orientation2d[0] == 'up':
            ori_labels = reversed(ori_labels)

        viewer.canvas.overlays.orientation_n = OrientationOverlay(
            visible=True, text=ori_labels[0], position='top_center'
        )
        viewer.canvas.overlays.orientation_s = OrientationOverlay(
            visible=True, text=ori_labels[1], position='bottom_center'
        )

    if (ori := horizontal_axis['orientation']) is not None:
        ori_labels = [v[0].upper() for v in ori['value'].split('-to-')]
        if viewer.scene.camera.orientation2d[1] == 'left':
            ori_labels = reversed(ori_labels)

        viewer.canvas.overlays.orientation_w = OrientationOverlay(
            visible=True, text=ori_labels[0], position='middle_left'
        )
        viewer.canvas.overlays.orientation_e = OrientationOverlay(
            visible=True, text=ori_labels[1], position='middle_right'
        )

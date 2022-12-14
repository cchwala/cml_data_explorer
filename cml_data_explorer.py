import numpy as np
import panel as pn
import hvplot.xarray
from holoviews.streams import Selection1D
from holoviews import opts
from holoviews.operation.datashader import rasterize
import holoviews as hv
from functools import partial


def plot(
    ds_cml_for_map,
    ds_for_ts,
    map_var='rainfall_amount',
    ts_vars=['trsl', 'rainfall_amount'],
    ts_ylims=[(40, 100), (0, 20)],
    tiles='OSM',
):
    
    ds_cml_for_map.coords['lon_center'] = (ds_cml_for_map.site_0_lon + ds_cml_for_map.site_1_lon)/2
    ds_cml_for_map.coords['lat_center'] = (ds_cml_for_map.site_0_lat + ds_cml_for_map.site_1_lat)/2
    if 'channel_id' in ds_cml_for_map.dims:
        ds_cml_for_map = ds_cml_for_map.isel(channel_id=0)
    
    if 'time' in ds_cml_for_map[map_var].dims:
        groupby='time'
    else:
        groupby=None
        
    sc = ds_cml_for_map[map_var].hvplot.scatter(
        'lon_center', 
        'lat_center', 
        color=map_var, 
        groupby=groupby,
        #clim=(0.1, 100), # for some reason, this has no effect...
        cmap='turbo',
        width=500,
        height=600,
        hover_cols=['cml_id', 'length', 'frequency'],
        tools=['tap', 'hover'],
        #geo=True,
        #tiles=tiles,
    )

    stream = Selection1D(source=sc)

    def plot_cml_ts(index, var_name):
        if not index:
            label = 'no selection'
            # Akward way to produce something that datashader will render as invisible.
            # It will produce data for t_0, t_1 and t_-1 with [value, NaN, value]. 
            data = ds_for_ts.isel(cml_id=0, time=[0, 1, -1])[var_name].astype('float').copy()
            values = data.values.copy()
            values[1] = np.NaN
            data.values = values 
        else:
            data = ds_for_ts.isel(cml_id=index[0])[var_name].astype('float')

        if index:
            label = str(ds_for_ts.isel(cml_id=index[0]).cml_id.values)
       
        if 'channel_id' in data.dims:
            return hv.NdOverlay(
                {
                    channel_id: 
                        hv.Curve(data.sel(channel_id=channel_id)).relabel(label)
                        for channel_id in data.channel_id.values
                },
                kdims='channel_id',
            )
        else:
            return hv.Curve(data).relabel(label)
    
    curves_ts_var = [
        rasterize(
            hv.DynamicMap(partial(plot_cml_ts, var_name=ts_var), kdims=[], streams=[stream]),
            #line_width=1,
            #pixel_ratio=2,
            aggregator='any',
            #cmap=['red'],
        ).opts(ylim=ts_ylim)
        for ts_var, ts_ylim in zip(ts_vars, ts_ylims)
    ]
    
    #ts_var2 = hv.DynamicMap(partial(plot_cml_ts, var_name=ts_vars[1]), kdims=[], streams=[stream]).opts(ylim=(-5, 50))
    
    xs = list(zip(ds_cml_for_map.site_0_lon.values, ds_cml_for_map.site_1_lon.values))
    ys = list(zip(ds_cml_for_map.site_0_lat.values, ds_cml_for_map.site_1_lat.values))
    cml_lines = hv.Segments(data=[(x[0], y[0], x[1], y[1]) for x, y in zip(xs, ys)]).opts(color='k')

    fig = pn.Row(
        pn.panel(cml_lines * sc.opts(toolbar='above', active_tools=['pan','wheel_zoom', 'tap']), widget_location='top_left'),
        pn.Column(
            *[pn.panel(curve_ts_var.opts(toolbar='above', width=800, active_tools=['pan','wheel_zoom']))
             for curve_ts_var in curves_ts_var
            ]
            #pn.panel(ts_var2.opts(toolbar='above', width=800, active_tools=['pan','wheel_zoom'])),
        ),
    )
    return fig

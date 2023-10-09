
export class Playback
{
    constructor(callback)
    {
        this.callback = callback;
        this.run = false;
        this.frame = 0;
        this.min = 0;
        this.max = 0;
        this.duration = 180;
        this.fps = 60;
        this.request_id = null;
        this.start_frame = null;
        this.start_time = null;
    }

    _request_frame()
    {
        this.request_id = window.requestAnimationFrame(this._on_frame.bind(this));
    }

    set_range(min, max)
    {
        this.min = min;
        this.max = max;
        this.duration = max - min;
        this.frame = min;
        this.callback(this.frame);
    }

    start()
    {
        this.run = true;
        this.start_time = null;
        this.start_frame = this.frame;
        this._request_frame();
    }

    _on_frame(timer)
    {
        if ( this.start_time == null )
            this.start_time = timer;

        let delta_frames = this.start_frame + (timer - this.start_time) / 1000 * this.fps;
        this.frame = this.min + (delta_frames % this.duration);
        this.callback(this.frame);

        if ( this.run )
            this._request_frame();
    }

    stop()
    {
        this.run = false;
        if ( this.request_id !== null )
            window.cancelAnimationFrame(this.request_id);
    }

    go_to(frame)
    {
        this.frame = frame;
        this.callback(this.frame);
    }
}

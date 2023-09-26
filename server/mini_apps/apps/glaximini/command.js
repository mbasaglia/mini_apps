class Command
{
    constructor(data, autocommit)
    {
        this.data = data;
        this.committed = false;
        this.autocommit = autocommit;
    }

    redo(editor)
    {
    }

    undo(editor)
    {
    }

    merge(other)
    {
        if ( this.committed || !other || other.constructor.name != this.constructor.name )
            return false;

        return this.on_merge(other);
    }

    on_merge(data, other_data)
    {
        return false;
    }

    to_remote_command_undo()
    {
    }

    to_remote_command_redo()
    {
    }
}

function array_equal(a, b)
{
    if ( a.length != b.length )
        return false;

    for ( let i = 0; i < a.length; i++ )
        if ( a[i] != b[i] )
            return false;

    return true;
}

export class ShapeEditCommand extends Command
{
    constructor(ids, before, after, autocommit)
    {
        super({ids, before, after}, autocommit);
    }

    to_remote_command_redo()
    {
        return {
            command: "shape.edit",
            data: {ids: this.data.ids, props: this.data.after, timestamp: new Date().getTime()},
        }
    }

    to_remote_command_undo()
    {
        return {
            command: "shape.edit",
            data: {ids: this.data.ids, props: this.data.before, timestamp: new Date().getTime()},
        }
    }

    on_merge(other)
    {
        if ( !array_equal(this.data.ids, other.data.ids) )
            return false;

        let keys = Object.keys(this.data.after).sort();
        let okeys = Object.keys(other.data.after).sort();
        if ( !array_equal(keys, okeys) )
            return false;

        this.data.after = other.data.after;
        return true;
    }

    redo(editor)
    {
        for ( let id of this.data.ids )
            editor.update_object(id, this.data.after);
    }

    undo(editor)
    {
        for ( let id of this.data.ids )
            editor.update_object(id, this.data.before);
    }

    static from_remote(data)
    {
        return new ShapeEditCommand(data.ids, {}, data.props);
    }
}

export class ShapeDeleteCommand extends Command
{
    constructor(id)
    {
        super({id}, true);
    }


    redo(editor)
    {
        editor.get_object(this.data.id).remove();
    }

    undo(editor)
    {
        editor.get_object(this.data.id).insert();
    }

    to_remote_command_redo()
    {
        return {
            command: "shape.delete",
            data: {id: this.data.id},
        }
    }

    to_remote_command_undo()
    {
        return {
            command: "shape.add",
            data: {id: this.data.id},
        }
    }

    static from_remote(data)
    {
        return new ShapeDeleteCommand(data.id);
    }
}


export class ShapeAddCommand extends Command
{
    constructor(shape, props, id)
    {
        let data = {};
        if ( props ) data.props = props;
        if ( id ) data.id = id;
        if ( shape ) data.shape = shape;
        super(data, true);
    }


    redo(editor)
    {
        editor.shape_from_command(this.data);
    }

    undo(editor)
    {
        editor.get_object(this.data.id).remove();
    }

    to_remote_command_redo()
    {
        return {
            command: "shape.add",
            data: this.data,
        }
    }

    to_remote_command_undo()
    {
        return {
            command: "shape.delete",
            data: {id: this.data.id},
        }
    }

    static from_remote(data)
    {
        return new ShapeAddCommand(data.shape, data.props, data.id);
    }
}

export class KeyframeAddCommand extends Command
{

    constructor(id, time, props)
    {
        super({id, time, props}, true);
    }


    redo(editor)
    {
        editor.get_object(this.data.id).add_keyframe(this.data.time, this.data.props);
    }

    undo(editor)
    {
        editor.get_object(this.data.id).remove_keyframe(this.data.time);
    }

    to_remote_command_redo()
    {
        return {
            command: "keyframe.add",
            data: this.data,
        }
    }

    to_remote_command_undo()
    {
        return {
            command: "keyframe.delete",
            data: {id: this.data.id, time: this.data.time},
        }
    }

    static from_remote(data)
    {
        return new KeyframeAddCommand(data.id, data.time, data.props);
    }
}


export class ShapeParentCommand extends Command
{

    constructor(child, after, before)
    {
        super({child, after, before}, true);
    }


    redo(editor)
    {
        if ( this.data.before === undefined )
        {
            let shape = editor.get_object(this.data.child);
            if ( shape.parent )
                this.data.before = shape.parent.id;
            else
                this.data.before = null;
        }

        editor.set_parent(this.data.child, this.data.after);
    }

    undo(editor)
    {
        editor.set_parent(this.data.child, this.data.before);
    }

    to_remote_command_redo()
    {
        return {
            command: "shape.parent",
            data: {child: this.child, parent: this.after},
        }
    }

    to_remote_command_undo()
    {
        return {
            command: "shape.parent",
            data: {child: this.child, parent: this.before},
        }
    }

    static from_remote(data)
    {
        return new ShapeParentCommand(data.child, data.parent);
    }
}


export class EventDestroyer
{
    constructor()
    {
        this.events = [];
    }

    add(target, name, func)
    {
        this.events.push([target, name, func]);
        target.addEventListener(name, func);
    }

    destroy()
    {
        for ( let [target, name, func] of this.events )
            target.removeEventListener(name, func);

        this.events = [];
    }
}

export class CommandStack
{
    constructor(editor, connection)
    {
        this.editor = editor;
        this.connection = connection;
        this.ev = new EventDestroyer();
        this.ev.add(connection, "document.edit", this.on_remote.bind(this));
        this.commands = [];
        this.undone_commands = [];
        this.metas = {
            "shape.edit": ShapeEditCommand,
            "shape.delete": ShapeDeleteCommand,
            "shape.add": ShapeAddCommand,
            "keyframe.add": KeyframeAddCommand,
            "shape.parent": ShapeParentCommand,
        }
    }

    last()
    {
        return this.commands[this.commands.length-1];
    }

    _push_merge(command)
    {
        if ( this.commands.length > 0 )
        {
            if ( this.last().merge(command) )
            {
                this.connection.send({type: "document.edit", ...command.to_remote_command_redo()});
                return this.last();
            }

            this.commit(this.last());
        }


        this.commands.push(command);
        return command;
    }

    push(command)
    {
        this.undone_commands = [];

        command.redo(this.editor);

        this._push_merge(command);

        if ( command.autocommit )
            this.commit(this.last());
    }

    commit(command)
    {
        if ( command === undefined )
            command = this.last();

        if ( !command.committed )
        {
            command.committed = true;
            this.connection.send({type: "document.edit", ...command.to_remote_command_redo()});
        }
    }

    on_remote(ev)
    {
        this.metas[ev.detail.command].from_remote(ev.detail.data).redo(this.editor);
    }

    edit_command(shapes, props, autocommit)
    {
        if ( !Array.isArray(shapes) )
            shapes = [shapes];

        let objects = [];
        let ids = [];
        for ( let shape of shapes )
        {
            if ( typeof shape != "object" )
                shape = this.editor.get_object(shape);

            objects.push(shape);
            ids.push(shape.id);
        }

        if ( objects.length == 0 )
            return null;

        let before = Object.fromEntries(Object.keys(props).map(e => [e, objects[0].props[e]]));
        let cmd = new ShapeEditCommand(ids, before, props, autocommit);
        this.push(cmd);
        return cmd;
    }

    undo()
    {
        if ( this.commands.length == 0 )
            return;

        let command = this.commands.pop();
        this.undone_commands.unshift(command);
        command.committed = true;

        command.undo(this.editor);
        this.connection.send({type: "document.edit", ...command.to_remote_command_undo()});

        this.editor.on_edit();
    }

    redo()
    {
        if ( this.undone_commands.length == 0 )
            return;

        let command = this.undone_commands.shift();
        this.commands.push(command);

        command.redo(this.editor);
        this.connection.send({type: "document.edit", ...command.to_remote_command_redo()});

        this.editor.on_edit();
    }
}


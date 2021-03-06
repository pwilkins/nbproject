/* docView Plugin 
 * Depends:
 *    ui.core.js
 *     ui.view.js
 *

 Author 
 cf AUTHORS.txt 

 License
 Copyright (c) 2010-2012 Massachusetts Institute of Technology.
 MIT License (cf. MIT-LICENSE.txt or http://www.opensource.org/licenses/mit-license.php)
*/
/*global YT:true jQuery:true console:true*/
(function($) {
    var V_OBJ = $.extend({},$.ui.view.prototype,{
        _create: function() {
        $.ui.view.prototype._create.call(this);
        var self = this;
        self.element.append("<div class='util'/><div class='contents'/>");
        self._last_clicked_selection =  0;
        //SACHA: TODO These are sample values: 
        self._w = 800;
        self._h = 600;//sample init
        self._scale = 33;
        self.SEC_MULT_FACTOR = 100;
        self.___best_fit =  true;
        self.___best_fit_zoom =  1.0; //this is computed later
        self._page =  null; 
        self._id_source =  null;
        self._player = null;
        self._id_location       = null; //location_id of selected thread
        },
        _defaultHandler: function(evt){
        var self    = this;
        var id_source    = self._id_source;
        var model    = self._model;
        if (id_source !== $.concierge.get_state("file")){
            return;
        }
        /*
         * From now on, we assume the event is directed to this view ! 
         */ 
        switch (evt.type){
        case "zoom": 
        self.___best_fit =  false;
        self._render();
        break;
        case "note_hover": 
        $("div.selection[id_item="+evt.value+"]", self.element).addClass("hovered");
        break;
        case "note_out":
        $("div.selection[id_item="+evt.value+"]", self.element).removeClass("hovered");
        break;
        case "visibility":
        var fct = evt.value ? "show":"hide";
        $("div.selections, self.element")[fct]();
        break;
        case "global_editor": 
        var $editor = $("<div/>");
        $("div.global-editors", this.element).append($editor);
        $editor.editor();
        break;
        case "select_thread": 
        var o = model.o.location[evt.value];
        self._id_location = evt.value;
        self._page = self._model.o.location[self._id_location].page;
        self._player.seekTo(self._page/self.SEC_MULT_FACTOR);
        self._render();
        break;
        case "doc_scroll_down": 
        $.L("[docView11] TODO: doc_scroll_down");        
        break;
        case "doc_scroll_up": 
        $.L("[docView11] TODO: doc_scroll_up");        
        break;
        case "drawable_start": 
        self._player.pauseVideo();
        self._page = Math.floor(self.SEC_MULT_FACTOR*self._player.getCurrentTime());
        $("#docview_drawingarea").attr("page", self._page);
        break;
        case "editor_saving": 
        self._player.playVideo();
        break;
        }
        },
        select: function(){
        var id = this._id_source;
        if (id && id !== $.concierge.get_state("file")){
            $.concierge.trigger({type:"file", value:this._id_source });
        }
        }, 
        set_model: function(model, init_event){
        var self=this;
        //for now, we don't register to receive any particular updates.
        model.register($.ui.view.prototype.get_adapter.call(this),  {location: null});
        //build view: 
        var id_source = $.concierge.get_state("file");
        self._id_source =  id_source; 
        self._model =  model;
        self.element.addClass("docView");
        self._update_best_fit_zoom();
        self._generate_contents();
        self._render();
        if (init_event){
            $.concierge.trigger(init_event);
        }
        else{
            $.concierge.trigger({type:"page", value: 1});
        }
        if ($.concierge.activeView === null){
            $.concierge.activeView = self; //init. 
        }
        },
        _keydown: function(event){
        var thread_codes = {37: {sel: "prev", no_sel: "last", dir: "up", msg:"No more comments above..."}, 39: {sel: "next", no_sel:"first", dir: "down", msg:"No more comments below..."}}; 
        var scroll_codes = {38: "-=", 40: "+="};
        var new_sel, id_item, id_new;
        if (event.keyCode in thread_codes){
            var sel = $("div.selection.selected", this.element);
            if (sel.length){
            new_sel = sel[thread_codes[event.keyCode].sel]();
            if (new_sel.length){
                new_sel.click();
            }
            else { // we need to find next location on subsequent pages
                id_item = sel.attr("id_item");
                id_new = $.concierge.get_component("location_closestpage")({id: Number(id_item), model: this._model, direction: thread_codes[event.keyCode].dir}); 
                if (id_new !== null){
                $.concierge.trigger({type:"select_thread", value: id_new});
                }
                else{
                $.I( thread_codes[event.keyCode].msg);
                }
            }
            }            
            else{ // no selection on the page
            new_sel = $("div.selection")[thread_codes[event.keyCode].no_sel](); 
            if (new_sel.length){
                new_sel.click();
            }
            }
            return false;
        }
        else if (event.keyCode in scroll_codes){
            $.L("[docView11] TODO _keydown");
        }
        else{
            return true; // let the event be captured for other stuff
        }
        }, 
        update: function(action, payload, items_fieldname){            //TODO: this is exactly the same code as ui.notepaneview7.js: maybe we should factor it out ?             

        if (action === "add" && items_fieldname === "location"){
            var id_source    = this._id_source; 
            var page        = this._page;
            if (page === null || id_source === null ){
            //initial rendering: Let's render the first page. We don't check the id_source here since other documents will most likely have their page variable already set. 
            this._page =  1;
            this._render();
            //TODO: in other  "add location" cases we may have to use different method, that forces a to redraw the pages that have been rendered already. 
            }
            else{
            $.L("[docView11] TODO: update");
            }
        }
        else if (action === "remove" && items_fieldname === "location"){ //just re-render the pages where locations were just removed. 
            var D        = payload.diff;
            $.L("[docView11] TODO: remove");
        }
        }, 
        _update: function(){
        $.ui.view.prototype._update.call(this);
        var self = this;
        self._update_best_fit_zoom();
        //        self._render();
        //        self._generate_contents();
        },
        _update_best_fit_zoom: function(){        
                console.warn("TODO!");
        }, 
        close: function(){
        var id =  this._id_source;
        delete $.concierge.features["doc_viewer"][id];
        $.ui.view.prototype.close.call(this);
        $.L("closing docviewer",  id);
        },
        _generate_selections: function(){
        /* 
         *  unlike generate_contents, we always regenerate the selections, irrespective 
         *  of whether they were there previously or not
         */
        var self = this;
        var contents;
        var id_source = self._id_source ;
        var model = this._model;        
        var numpages = model.o.file[id_source].numpages;
        var t,l,w,h, ID, locs, o;
        var s = ($.concierge.get_constant("res")*self._scale+0.0)/($.concierge.get_constant("RESOLUTION_COORDINATES")*100);
        var file = model.o.file[id_source];
        var fudge = (file.rotation === 90 || file.rotation === 270 ? file.h : file.w)/612.0;
        s=s*fudge; //for compatibility with old UI, but needs to be changed !!!
        for (var p=1;p<=numpages;p++){            
            contents="";
            locs = model.get("location", {id_source: id_source, page: p}).sort(self.options.loc_sort_fct);
            //facet_page._filter(p, "", true);
            for (var i=0;i<locs.length;i++){
            o = locs[i];
            ID=o.ID;
            t=o.top*s;
            l=o.left*s;
            w=o.w*s;
            h=o.h*s;
            contents+=("<div class='selection' id_item='"+ID+"' style='top: "+t+"px; left: "+l+"px; width: "+w+"px; height: "+h+"px'/>");
            }
            $("div.material[page="+p+"]>div.selections",  self.element).html(contents);
        }
        $("div.material>div.selections>div.selection", self.element).mouseover(function(evt){
            var id_item = evt.currentTarget.getAttribute("id_item");
            $.concierge.trigger({type:"note_hover", value: id_item});
            }).mouseout(function(evt){
                var id_item=evt.currentTarget.getAttribute("id_item");
                $.concierge.trigger({type:"note_out", value: id_item});
            }).click(function(evt){
                var id_item=evt.currentTarget.getAttribute("id_item");
                $.concierge.trigger({type:"select_thread", value: id_item});
                });
        
        },
        _generate_contents: function(){
        /*
         * either generates or updates contents
         * we don't systematically generate it so we can keep the editors, drawables etc...
         */
        var self    = this;
        var contents    = "<div class='global-editors'/>";
        var id_source    = self._id_source;
        var model    = this._model;
        var file    = model.o.file[id_source];
        $.concierge.trigger({type: "scale", value: self._scale}); 
        var w        = self._w;
        var h        = self._h;
        var style    = "width: "+w+"px;height: "+h+"px";    
        contents+="<div class='material' style='"+style+"'><div id='docview_drawingarea'/><div class='selections'/><div id='youtube_player'/></div><div id='docview_controls'> <b><a href='#' id='docview_button_play'>Play</a></b> <b><a href='#'  id='docview_button_pause'>Pause</a></b></div>";
        $("div.contents", self.element).html(contents);
        $("#docview_drawingarea").drawable({model: self._model});
        $("#docview_button_play").click(function(evt){
            self._player.playVideo();
            });
        $("#docview_button_pause").click(function(evt){
            self._player.pauseVideo();
            });
        var $material = $("div.material", self.element).click(function(evt){
            var numpage = evt.currentTarget.getAttribute("page");
            $.concierge.trigger({type: "page", value:numpage});
            
            }).mouseenter(function(evt){
                var numpage = evt.currentTarget.getAttribute("page");
                if (numpage !== self._page){
                $.concierge.trigger({type: "page_peek", value:numpage});
                }
            });
        self._v_margin =  parseInt($material.css("margin-bottom") +  parseInt($material.css("margin-top"), 10), 10 );
        self._player = new YT.Player('youtube_player', {
            height: '390',
            width: '640',
            videoId: 'JtsyP0tnVRY',
            playerVars: {controls: 0}, 
            events: {
                'onReady': function(event){
                event.target.playVideo();
                },
                'onStateChange': function(event){
                $.L("[docView11] TODO: YouTube.onStateChange:  "+event);
                }
            }
            });
        },
        _render: function(){
        /*
         * this is where we implement the caching strategy we want...
         */
        var p = this._page;
        this._render_one(p);
        }, 
        _render_one: function(page){
        var self    = this;
        self._draw_selections(page);
        }, 
        _draw_selections: function(page){
        var self = this;
        var contents;
        var id_source = self._id_source ;
        var model = this._model;        
        var t,l,w,h, ID, locs, o, sel_contents;
        var s = ($.concierge.get_constant("res")*self._scale+0.0)/($.concierge.get_constant("RESOLUTION_COORDINATES")*100);
        var file = model.o.file[id_source];
        var fudge = (file.rotation === 90 || file.rotation === 270 ? file.h : file.w)/612.0;
        s=s*fudge; //BUG_226: for compatibility with old UI, but needs to be removed !!!
        contents="";
        locs = model.get("location", {id_source: id_source, page: page}).sort(self.options.loc_sort_fct);
        var me =  $.concierge.get_component("get_userinfo")();
        for (var i=0;i<locs.length;i++){
            o = locs[i];
            ID=o.ID;
            t=o.top*s;
            l=o.left*s;
            w=o.w*s;
            h=o.h*s;
            sel_contents = "";
            if (!(model.get("comment", {ID_location: ID, admin: 1}).is_empty())){
            sel_contents += "<div class='nbicon adminicon' title='An instructor/admin has participated to this thread'/>";
            }
            if (!(model.get("comment", {ID_location: ID, id_author: me.id}).is_empty())){
            if (model.get("comment", {ID_location: ID, type: 1}).is_empty()){
                sel_contents += "<div class='nbicon dark meicon' title='I participated to this thread'/>";
            }
            else{
                sel_contents += "<div class='nbicon privateicon' title='I have private comments in this thread'/>";
            }
            }
            contents+=("<div class='selection' id_item='"+ID+"' style='top: "+t+"px; left: "+l+"px; width: "+w+"px; height: "+h+"px'>"+sel_contents+"</div>");
        }    
        $("div.material>div.selections",  self.element).html(contents).children("div.selection").mouseover(function(evt){
            $.concierge.trigger({type:"note_hover", value: evt.currentTarget.getAttribute("id_item")});
            }).mouseout(function(evt){
                $.concierge.trigger({type:"note_out", value: evt.currentTarget.getAttribute("id_item")});
            }).click(function(evt){
                $.concierge.trigger({type:"select_thread", value: evt.currentTarget.getAttribute("id_item")});
                });
        var sel = model.o.location[self._id_location];
        if (sel && sel.page === page){//highlight selection
            $("div.selection[id_item="+self._id_location+"]",self.element).addClass("selected");
        }
        }
    });
    
    $.widget("ui.docView",V_OBJ );
    $.ui.docView.prototype.options = {
    img_server: "http://localhost", 
    loc_sort_fct: function(o1, o2){return o1.top-o2.top;},
    provides: ["doc"], 
    listens: {
        zoom: null, 
        note_hover: null, 
        note_out: null, 
        visibility: null, 
        global_editor: null, 
        select_thread: null,
        drawable_start: null,
        editor_saving: null
    }            
    };
})(jQuery);

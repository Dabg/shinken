

%print 'Host value?', host
%import time

%# If got no Host, bailout
%if not host:
%include header title='Invalid host'

Invalid host
%else:

%include header title='Host detail about ' + host.host_name


%helper = app.helper


<script type="text/javascript">
  var tabs = new MGFX.Tabs('.tab','.feature',{
  autoplay: false,
  transitionDuration:500,
  slideInterval:3000,
  hover:true
  });
</script>

<div id="left_container" class="grid_3">
  <div id="dummy_box" class="box_gradient_horizontal"> 
    <p>Dummy box</p>
  </div>
  <div id="nav_left">
    <ul>
      <li><a href="http://unitedseed.de/tmp/Meatball/host_detail.html#">Overview</a></li>
      <li><a href="http://unitedseed.de/tmp/Meatball/host_detail.html#">Detail</a></li>
    </ul>
  </div>
</div>
<div class="grid_13">
  <div id="host_preview">
    <h2 class="icon_warning">Warning: {{host.host_name}}</h2>
    <dl class="grid_6">
      <dt>Alias:</dt>
      <dd>{{host.alias}}</dd>
      
      <dt>Parents:</dt>
      %if len(host.parents) > 0:
      <dd> {{','.join([h.get_name() for h in host.parents])}}</dd>
      %else:
      <dd> No parents </dd>
      %end
      <dt>Members of:</dt>
      %if len(host.hostgroups) > 0:
      <dd> {{','.join([hg.get_name() for hg in host.hostgroups])}}</dd>
      %else:
      <dd> No groups </dd>
      %end
    </dl>
    <dl class="grid_6">
      <dt>Notes:</dt>
      <dd>{{host.notes}}</dd>
    </dl>
    <div class="grid_4">
      <img class="box_shadow host_img_80" src="/static/images/no_image.png">
    </div>
  </div>
  <hr>
  <div id="host_overview">
    <h2>Host Overview</h2>
    <div class="grid_6">
      <table>
	<tbody>
	  <tr>
	    <th scope="row" class="column1">Host Status</th>
	    <td><span class="state_ok icon_ok">{{host.state}}</span> (for {{helper.print_duration(host.last_state_change)}}) </td>
	  </tr>	
	  <tr class="odd">
	    <th scope="row" class="column1">Status Information</th>
	    <td>{{host.output}}</td>
	  </tr>	
	  <tr>
	    <th scope="row" class="column1">Performance Data</th>	
	    <td>{{host.perf_data}}</td>
	  </tr>
	  <tr>
	    <th scope="row" class="column1">Business impact</th>	
	    <td>{{host.business_impact}}</td>
	  </tr>	
	  <tr class="odd">
	    <th scope="row" class="column1">Current Attempt</th>
	    <td>{{host.attempt}}/{{host.max_check_attempts}} ({{host.state_type}} state)</td>
	  </tr>	
	  <tr>
	    <th scope="row" class="column1">Last Check Time</th>
	    <td title='Last check was at {{time.asctime(time.localtime(host.last_chk))}}'>was {{helper.print_duration(host.last_chk)}}</td>
	  </tr>	
	  <tr>
	    <th scope="row" class="column1">Check Latency / Duration</th>
	    <td>{{'%.2f' % host.latency}} / {{'%.2f' % host.execution_time}} seconds</td>
	  </tr>	
	  <tr class="odd">
	    <th scope="row" class="column1">Next Scheduled Active Check</th>
	    <td title='Next active check at {{time.asctime(time.localtime(host.next_chk))}}'>{{helper.print_duration(host.next_chk)}}</td>
	  </tr>	
	  <tr>
	    <th scope="row" class="column1">Last State Change</th>
	    <td>{{time.asctime(time.localtime(host.last_state_change))}}</td>
	  </tr>	
	  <tr class="odd">
	    <th scope="row" class="column1">Last Notification</th>
	    <td>{{helper.print_date(host.last_notification)}} (notification {{host.current_notification_number}})</td>
	  </tr>	
	  <tr>						
	    <th scope="row" class="column1">Is This Host Flapping?</th>
	    <td>{{helper.yes_no(host.is_flapping)}} ({{helper.print_float(host.percent_state_change)}}% state change)</td>

	  </tr>
	  <tr class="odd">
	    <th scope="row" class="column1">In Scheduled Downtime?</th>
	    <td>{{helper.yes_no(host.in_scheduled_downtime)}}</td>
	  </tr>	
	</tbody>
	<tbody>
	  <tr class="odd">
	    <th scope="row" class="column1">Active Checks</th>
	    <td class="icon_tick">{{helper.ena_disa(host.active_checks_enabled)}}</td>			
	  </tr>	
	  <tr>
	    <th scope="row" class="column1">Passive Checks</th>
	    <td class="icon_tick">{{helper.ena_disa(host.passive_checks_enabled)}}</td>
	  </tr>
	  <tr>
	    <th scope="row" class="column1">Obsessing</th>
	    <td class="icon_tick">{{helper.ena_disa(host.obsess_over_host)}}</td>
	  </tr>
	  <tr>
	    <th scope="row" class="column1">Notifications</th>
	    <td class="icon_cross">{{helper.ena_disa(host.notifications_enabled)}}</td>
	  </tr>
	  <tr>
	    <th scope="row" class="column1">Event Handler</th>
	    <td class="icon_tick">{{helper.ena_disa(host.event_handler_enabled)}}</td>
	  </tr>
	  <tr>
	    <th scope="row" class="column1">Flap Detection</th>
	    <td class="icon_cross">{{helper.ena_disa(host.flap_detection_enabled)}}</td>
	  </tr>
	</tbody>	
      </table>
    </div>
  </div>
  <div id="host_more">

  </div>
</div>

</div>
<div class="clear"></div>
<div id="footer" class="grid_16">
</div>
<div class="clear"></div>
</div>

%#End of the Host Exist or not case
%end

%include footer


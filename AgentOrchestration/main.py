"""Streamlit UI (refactored) for the Blog Agent.

This file replaces the previous monolithic UI and routes side-effect
operations through the focused service classes in `AgentOrchestration/services.py`.
The goal is to apply SRP and DI while preserving the UI experience.
"""

import streamlit as st
import json
from datetime import datetime

from blog_agent import process_blog_request
from AgentOrchestration.services import (
    AuthService,
    MetricsService,
    ChaosService,
    RecoveryService,
    DebugService,
)

# Instantiate services
auth_service = AuthService()
metrics_service = MetricsService()
chaos_service = ChaosService()
recovery_service = RecoveryService()
debug_service = DebugService()

# Session defaults
st.set_page_config(page_title="Blog Agent Interface", layout="wide")
st.title("AI Blog Agent")
st.markdown("---")

if 'blog_post' not in st.session_state:
    st.session_state.blog_post = None
if 'last_blogs' not in st.session_state:
    st.session_state.last_blogs = None
if 'response' not in st.session_state:
    st.session_state.response = None
if 'chaos_enabled' not in st.session_state:
    st.session_state.chaos_enabled = False
if 'chaos_failure_rate' not in st.session_state:
    st.session_state.chaos_failure_rate = 0.3

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Select Action", ["Create Blog", "Post Blog", "View Blogs", "Monitoring & Recovery"])

    st.markdown("---")
    st.subheader("System Info")
    try:
        m = metrics_service.get_metrics()
        st.metric("Total Requests", m.get('total_requests', 0))
        st.metric("Success Rate", f"{m.get('generation_success_rate', 0)}%")
        st.metric("Recovery Rate", f"{m.get('recovery_success_rate', 0)}%")
    except Exception as e:
        st.error(f"Error loading metrics: {e}")

    st.markdown("---")
    st.subheader("Chaos Control")
    chaos_quick_toggle = st.checkbox("Quick Enable/Disable", value=st.session_state.chaos_enabled, key="chaos_quick_toggle")
    if chaos_quick_toggle != st.session_state.chaos_enabled:
        st.session_state.chaos_enabled = chaos_quick_toggle
        st.rerun()

try:
    auth_service.login()
except Exception as e:
    st.warning(f"Login required: {e}")

if page == "Create Blog":
    st.subheader("Create New Blog Post")
    col1, col2 = st.columns(2)
    with col1:
        blog_title = st.text_input("Blog Title", placeholder="Enter blog post title", key="create_title")
    with col2:
        blog_category = st.selectbox("Category", ["Technology", "Business", "Lifestyle", "Education", "Other"], key="category")

    instructions = st.text_area("Content Instructions", placeholder="Describe what you want in the blog post", height=150, key="instructions")

    if st.button("Generate Blog", key="generate_btn"):
        if blog_title and instructions:
            with st.spinner("Generating blog post..."):
                try:
                    user_message = f"Create a blog post titled '{blog_title}' in the {blog_category} category with the following instructions: {instructions}"
                    response = process_blog_request(user_message)
                    if response.get('success'):
                        st.session_state.response = response
                        st.success("Blog post generated successfully!")
                        with st.expander("View Generated Content", expanded=True):
                            st.write(response.get('content'))
                        # Try to parse JSON
                        try:
                            if isinstance(response.get('content'), str):
                                blog_data = json.loads(response.get('content'))
                                st.session_state.blog_post = blog_data
                        except Exception:
                            st.session_state.blog_post = {"title": blog_title, "content": response.get('content')}
                    else:
                        st.error(f"Error: {response.get('content')}")
                except Exception as e:
                    st.error(f"Error generating blog: {e}")
        else:
            st.warning("Please fill in all required fields.")

elif page == "Post Blog":
    st.subheader("Post Blog to Platform")
    if st.session_state.blog_post:
        st.success("Blog post ready to post")
        with st.expander("Preview Blog Post"):
            if isinstance(st.session_state.blog_post, dict):
                st.write(f"**Title:** {st.session_state.blog_post.get('title','N/A')}")
                st.write(f"**Content:** {st.session_state.blog_post.get('content','N/A')[:200]}...")
            else:
                st.write(st.session_state.blog_post)

        if st.button("Post Blog Now", key="post_btn"):
            with st.spinner("Posting blog..."):
                try:
                    blog_post_json = json.dumps(st.session_state.blog_post) if isinstance(st.session_state.blog_post, dict) else st.session_state.blog_post
                    user_message = f"Post this blog to the platform: {blog_post_json}"
                    response = process_blog_request(user_message)
                    if response.get('success'):
                        st.success("Blog posted successfully!")
                        st.write(response.get('content'))
                    else:
                        st.error(f"Error posting blog: {response.get('content')}")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("No blog post to post. Please create one first.")

elif page == "View Blogs":
    st.subheader("View Recent Blogs")
    num_blogs = st.slider("Number of blogs to retrieve", 1, 10, 3, key="num_blogs")
    if st.button("Retrieve Blogs", key="retrieve_btn"):
        with st.spinner(f"Retrieving last {num_blogs} blogs..."):
            try:
                user_message = f"Retrieve the last {num_blogs} blog posts"
                response = process_blog_request(user_message)
                if response.get('success'):
                    st.success("Blogs retrieved successfully!")
                    st.session_state.last_blogs = response.get('content')
                    with st.expander("View Content", expanded=True):
                        st.write(response.get('content'))
                else:
                    st.error(f"Error retrieving blogs: {response.get('content')}")
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Monitoring & Recovery":
    st.subheader("System Monitoring & Recovery")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Metrics", "Checkpoints", "Recovery", "Chaos", "Logs", "Debugging"])

    with tab1:
        st.subheader("System Metrics")
        try:
            cm = metrics_service.get_metrics()
            st.metric("Total Requests", cm.get('total_requests', 0))
            st.metric("Success Rate", f"{cm.get('generation_success_rate',0)}%")
        except Exception as e:
            st.error(f"Error loading metrics: {e}")

    with tab2:
        st.subheader("Checkpoint Management")
        try:
            cps = recovery_service.get_checkpoints()
            if cps:
                st.success(f"Found {len(cps)} checkpoints")
                with st.expander("Checkpoint List", expanded=True):
                    for i, cp in enumerate(cps, 1):
                        st.write(f"{i}. {cp}")
            else:
                st.info("No checkpoints found yet.")
        except Exception as e:
            st.error(f"Error loading checkpoints: {e}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear All Checkpoints", key="clear_cp"):
                with st.spinner("Clearing checkpoints..."):
                    try:
                        result = recovery_service.clear()
                        if result.get('status') == 'success':
                            st.success(result.get('message'))
                        else:
                            st.error(result.get('error'))
                    except Exception as e:
                        st.error(f"Error clearing checkpoints: {e}")

    with tab3:
        st.subheader("Manual Recovery")
        try:
            cps = recovery_service.get_checkpoints()
            if cps:
                sel = st.selectbox("Select checkpoint to recover from", cps, key="recovery_cp")
                if st.button("Recover", key="recover_btn"):
                    with st.spinner(f"Recovering from '{sel}'..."):
                        resp = recovery_service.recover(sel)
                        if resp.get('success'):
                            st.success("Recovery successful!")
                            with st.expander("Recovery Content"):
                                st.write(resp.get('content'))
                        else:
                            st.error(f"Recovery failed: {resp.get('content')}")
            else:
                st.warning("No checkpoints available for recovery.")
        except Exception as e:
            st.error(f"Error during recovery: {e}")

    with tab4:
        st.subheader("Chaos Testing")
        failure_rate = st.slider("Failure Rate (%)", 0, 100, int(st.session_state.chaos_failure_rate*100), step=5, key="failure_rate_slider")
        if failure_rate / 100 != st.session_state.chaos_failure_rate:
            st.session_state.chaos_failure_rate = failure_rate / 100
            st.rerun()

        chaos_enabled_toggle = st.checkbox("Enable Chaos Testing", value=st.session_state.chaos_enabled, key="chaos_toggle_main")
        if chaos_enabled_toggle != st.session_state.chaos_enabled:
            st.session_state.chaos_enabled = chaos_enabled_toggle
            st.rerun()

        if st.session_state.chaos_enabled:
            chaos_service.enable(st.session_state.chaos_failure_rate)
        else:
            chaos_service.disable()

        try:
            cm = chaos_service.get_metrics()
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Status", "ACTIVE" if cm.get('chaos_enabled') else "INACTIVE")
            col2.metric("Configured Failure Rate", f"{cm.get('failure_rate',0)}%")
            col3.metric("Session Failure Rate", f"{st.session_state.chaos_failure_rate*100:.0f}%")
            if st.button("Reset Chaos Metrics", key="reset_chaos_metrics"):
                res = chaos_service.reset_metrics()
                st.success(res.get('message','Reset'))
                st.rerun()
        except Exception as e:
            st.error(f"Error loading chaos metrics: {e}")

    with tab5:
        st.subheader("System Logs")
        from pathlib import Path
        log_dir = Path("logs")
        if log_dir.exists():
            files = list(log_dir.glob("*.log"))
            if files:
                sel = st.selectbox("Select log file", [f.name for f in sorted(files, reverse=True)], key="log_file")
                try:
                    content = (log_dir/sel).read_text()
                    st.text_area("Log Content", value=content, height=400, disabled=True)
                    st.download_button("Download Log", data=content, file_name=sel)
                except Exception as e:
                    st.error(f"Error reading log file: {e}")
            else:
                st.info("No log files found yet.")
        else:
            st.warning("Logs directory not found.")

    with tab6:
        st.subheader("Debugging & Raw Traces")
        try:
            masked = debug_service.get_masked_key()
            st.text_input("LangSmith API Key (masked)", value=masked, disabled=True, key="ls_key_masked")
        except Exception as e:
            st.error(f"Error reading LangSmith key: {e}")

        try:
            logs = debug_service.get_debug_logs()
            st.write(f"Total debug entries: {len(logs)}")
            if logs:
                if st.button("Download Debug Logs", key="download_debug_logs"):
                    dump = json.dumps(logs, indent=2, ensure_ascii=False)
                    st.download_button(label="Download JSON", data=dump, file_name=f"debug_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")
                with st.expander("Show latest logs", expanded=False):
                    for entry in reversed(logs[-50:]):
                        st.markdown(f"**{entry.get('timestamp','-')} | {entry.get('model','-')}**")
                        st.code(json.dumps(entry, indent=2, ensure_ascii=False), language='json')
                if st.button("Clear Debug Logs", key="clear_debug_logs"):
                    debug_service.clear_debug_logs()
                    st.success("Debug logs cleared")
                    st.rerun()
            else:
                st.info("No debug logs yet.")
        except Exception as e:
            st.error(f"Error loading debug logs: {e}")

st.markdown("---")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Action",
        ["📝 Create Blog", "📤 Post Blog", "📚 View Blogs", "📊 Monitoring & Recovery"]
    )
    
    st.markdown("---")
    st.subheader("ℹ️ System Info")
    
    try:
        metrics = get_metrics()
        st.metric("Total Requests", metrics['total_requests'])
        st.metric("Success Rate", f"{metrics['generation_success_rate']}%")
        st.metric("Recovery Rate", f"{metrics['recovery_success_rate']}%")
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
    
    st.markdown("---")
    st.subheader("🔥 Chaos Control")
    
    # Sync session state with backend on every rerun
    # if st.session_state.chaos_enabled:
    #     enable_chaos_testing(st.session_state.chaos_failure_rate)
    #     st.success("🔥 CHAOS MODE: ACTIVE")
    # else:
    #     disable_chaos_testing()
    #     st.info("✅ CHAOS MODE: INACTIVE")
    
    # Quick chaos toggle
    chaos_quick_toggle = st.checkbox(
        "Quick Enable/Disable",
        value=st.session_state.chaos_enabled,
        key="chaos_quick_toggle"
    )
    
    if chaos_quick_toggle != st.session_state.chaos_enabled:
        st.session_state.chaos_enabled = chaos_quick_toggle
        st.rerun()

try:
    login()
except Exception as e:
    st.warning(f"⚠️ Login required: {e}")

if page == "📝 Create Blog":
    st.subheader("✍️ Create New Blog Post")
    st.info("Generate a new blog post using AI.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        blog_title = st.text_input(
            "Blog Title",
            placeholder="Enter blog post title",
            key="create_title"
        )
    
    with col2:
        blog_category = st.selectbox(
            "Category",
            ["Technology", "Business", "Lifestyle", "Education", "Other"],
            key="category"
        )
    
    instructions = st.text_area(
        "Content Instructions",
        placeholder="Describe what you want in the blog post (tone, style, key points, etc.)",
        height=150,
        key="instructions"
    )
    
    if st.button("🎨 Generate Blog", use_container_width=True, key="generate_btn"):
        if blog_title and instructions:
            with st.spinner("✨ Generating blog post..."):
                try:
                    user_message = f"Create a blog post titled '{blog_title}' in the {blog_category} category with the following instructions: {instructions}"
                    response = process_blog_request(user_message)
                    
                    if response['success']:
                        st.session_state.response = response
                        st.success("✅ Blog post generated successfully!")
                        
                        with st.expander("📄 View Generated Content", expanded=True):
                            st.write(response['content'])
                        
                        # Try to parse as JSON if it's a blog post
                        try:
                            if isinstance(response['content'], str):
                                blog_data = json.loads(response['content'])
                                st.session_state.blog_post = blog_data
                        except json.JSONDecodeError:
                            st.session_state.blog_post = {"title": blog_title, "content": response['content']}
                        
                        # Display metrics
                        with st.expander("📊 Metrics"):
                            metrics_data = response['metadata']['metrics']
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Total Requests", metrics_data['total_requests'])
                            col2.metric("Successful Generations", metrics_data['successful_generations'])
                            col3.metric("Failed Generations", metrics_data['failed_generations'])
                            col4.metric("Success Rate", f"{metrics_data['generation_success_rate']}%")
                    else:
                        st.error(f"❌ Error: {response['content']}")
                except Exception as e:
                    st.error(f"❌ Error generating blog: {str(e)}")
        else:
            st.warning("⚠️ Please fill in all required fields.")

elif page == "📤 Post Blog":
    st.subheader("📤 Post Blog to Platform")
    st.info("This action will save your blog post to the platform.")
    
    if st.session_state.blog_post:
        st.success("✅ Blog post ready to post")
        
        with st.expander("👁️ Preview Blog Post"):
            if isinstance(st.session_state.blog_post, dict):
                st.write(f"**Title:** {st.session_state.blog_post.get('title', 'N/A')}")
                st.write(f"**Content:** {st.session_state.blog_post.get('content', 'N/A')[:200]}...")
            else:
                st.write(st.session_state.blog_post)
        
        if st.button("🚀 Post Blog Now", use_container_width=True, key="post_btn"):
            with st.spinner("📤 Posting blog..."):
                try:
                    blog_post_json = json.dumps(st.session_state.blog_post) if isinstance(st.session_state.blog_post, dict) else st.session_state.blog_post
                    user_message = f"Post this blog to the platform: {blog_post_json}"
                    response = process_blog_request(user_message)
                    
                    if response['success']:
                        st.success("✅ Blog posted successfully!")
                        st.write(response['content'])
                        
                        with st.expander("📊 Metrics"):
                            metrics_data = response['metadata']['metrics']
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Total Posts", metrics_data['successful_posts'])
                            col2.metric("Failed Posts", metrics_data['failed_posts'])
                            col3.metric("Success Rate", f"{metrics_data['generation_success_rate']}%")
                            col4.metric("Uptime (seconds)", int(metrics_data['uptime_seconds']))
                    else:
                        st.error(f"❌ Error posting blog: {response['content']}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("⚠️ No blog post to post. Please create one first in the 'Create Blog' section.")
        if st.button("Go to Create Blog Section"):
            st.switch_page("pages/📝 Create Blog")

elif page == "📚 View Blogs":
    st.subheader("📚 View Recent Blogs")
    st.info("Retrieve and view the last n blog posts from the platform.")
    
    num_blogs = st.slider(
        "Number of blogs to retrieve",
        min_value=1,
        max_value=10,
        value=3,
        key="num_blogs"
    )
    
    if st.button("🔍 Retrieve Blogs", use_container_width=True, key="retrieve_btn"):
        with st.spinner(f"📚 Retrieving last {num_blogs} blogs..."):
            try:
                user_message = f"Retrieve the last {num_blogs} blog posts"
                response = process_blog_request(user_message)
                
                if response['success']:
                    st.success("✅ Blogs retrieved successfully!")
                    st.session_state.last_blogs = response['content']
                    
                    with st.expander("📄 View Content", expanded=True):
                        st.write(response['content'])
                    
                    with st.expander("📊 Metrics"):
                        metrics_data = response['metadata']['metrics']
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Total Requests", metrics_data['total_requests'])
                        col2.metric("Successful Retrievals", metrics_data['successful_posts'])
                        col3.metric("Success Rate", f"{metrics_data['generation_success_rate']}%")
                        col4.metric("Uptime (seconds)", int(metrics_data['uptime_seconds']))
                else:
                    st.error(f"❌ Error retrieving blogs: {response['content']}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

elif page == "📊 Monitoring & Recovery":
    st.subheader("📊 System Monitoring & Recovery")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Metrics", "💾 Checkpoints", "🔄 Recovery", "🔥 Chaos Testing", "📋 Logs", "🛠 Debugging"])
    
    # TAB 1: METRICS
    with tab1:
        st.subheader("📈 System Metrics")
        try:
            current_metrics = get_metrics()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Requests", current_metrics['total_requests'])
            with col2:
                st.metric("Successful Generations", current_metrics['successful_generations'])
            with col3:
                st.metric("Failed Generations", current_metrics['failed_generations'])
            with col4:
                st.metric("Success Rate", f"{current_metrics['generation_success_rate']}%")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Successful Posts", current_metrics['successful_posts'])
            with col2:
                st.metric("Failed Posts", current_metrics['failed_posts'])
            with col3:
                st.metric("Recovery Attempts", current_metrics['recovery_attempts'])
            with col4:
                st.metric("Successful Recoveries", current_metrics['successful_recoveries'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Recovery Success Rate", f"{current_metrics['recovery_success_rate']}%")
            with col2:
                uptime_hours = current_metrics['uptime_seconds'] / 3600
                st.metric("Uptime", f"{uptime_hours:.2f} hours")
        except Exception as e:
            st.error(f"Error loading metrics: {e}")
    
    # TAB 2: CHECKPOINTS
    with tab2:
        st.subheader("💾 Checkpoint Management")
        
        try:
            checkpoints = get_checkpoints()
            
            if checkpoints:
                st.success(f"✅ Found {len(checkpoints)} checkpoints")
                
                with st.expander("📋 Checkpoint List", expanded=True):
                    for i, cp in enumerate(checkpoints, 1):
                        st.write(f"{i}. `{cp}`")
            else:
                st.info("ℹ️ No checkpoints found yet.")
        except Exception as e:
            st.error(f"Error loading checkpoints: {e}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear All Checkpoints", use_container_width=True, key="clear_cp"):
                with st.spinner("Clearing checkpoints..."):
                    try:
                        result = clear_checkpoints()
                        if result['status'] == 'success':
                            st.success(f"✅ {result['message']}")
                        else:
                            st.error(f"❌ {result['error']}")
                    except Exception as e:
                        st.error(f"Error clearing checkpoints: {e}")
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True, key="refresh_cp"):
                st.rerun()
    
    # TAB 3: RECOVERY
    with tab3:
        st.subheader("🔄 Manual Recovery")
        
        try:
            checkpoints = get_checkpoints()
            
            if checkpoints:
                selected_checkpoint = st.selectbox(
                    "Select checkpoint to recover from",
                    checkpoints,
                    key="recovery_cp"
                )
                
                if st.button("🚀 Recover from Checkpoint", use_container_width=True, key="recover_btn"):
                    with st.spinner(f"Recovering from '{selected_checkpoint}'..."):
                        try:
                            response = recover_from_checkpoint(selected_checkpoint)
                            
                            if response['success']:
                                st.success("✅ Recovery successful!")
                                with st.expander("📄 Recovery Content"):
                                    st.write(response['content'])
                            else:
                                st.error(f"❌ Recovery failed: {response['content']}")
                        except Exception as e:
                            st.error(f"Error during recovery: {e}")
            else:
                st.warning("⚠️ No checkpoints available for recovery.")
        except Exception as e:
            st.error(f"Error loading recovery options: {e}")
    
    # TAB 4: CHAOS TESTING
    with tab4:
        st.subheader("🔥 Chaos Testing")
        st.info("Inject random failures to test resilience and recovery mechanisms.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            failure_rate = st.slider(
                "Failure Rate (%)",
                min_value=0,
                max_value=100,
                value=int(st.session_state.chaos_failure_rate * 100),
                step=5,
                key="failure_rate_slider"
            )
            # Update session state immediately
            if failure_rate / 100 != st.session_state.chaos_failure_rate:
                st.session_state.chaos_failure_rate = failure_rate / 100
                st.rerun()
        
        with col2:
            chaos_enabled_toggle = st.checkbox(
                "Enable Chaos Testing",
                value=st.session_state.chaos_enabled,
                key="chaos_toggle_main"
            )
            # Update session state immediately
            if chaos_enabled_toggle != st.session_state.chaos_enabled:
                st.session_state.chaos_enabled = chaos_enabled_toggle
                st.rerun()
        
        # Auto-apply settings on every render
        if st.session_state.chaos_enabled:
            enable_chaos_testing(st.session_state.chaos_failure_rate)
        else:
            disable_chaos_testing()
        
        st.markdown("---")
        
        # Chaos Status
        st.subheader("📊 Chaos Status")
        try:
            chaos_metrics = get_chaos_metrics()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Status", "🔥 ACTIVE" if chaos_metrics['chaos_enabled'] else "✅ INACTIVE")
            with col2:
                st.metric("Configured Failure Rate", f"{chaos_metrics['failure_rate']}%")
            with col3:
                st.metric("Session Failure Rate", f"{st.session_state.chaos_failure_rate * 100:.0f}%")
        except Exception as e:
            st.error(f"Error loading chaos status: {e}")
        
        st.markdown("---")
        
        # Chaos Metrics
        st.subheader("📈 Chaos Testing Metrics")
        try:
            chaos_metrics = get_chaos_metrics()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Injections", chaos_metrics['total_injections'])
            with col2:
                st.metric("Successful Injections", chaos_metrics['successful_injections'])
            with col3:
                st.metric("Failed Injections", chaos_metrics['total_injections'] - chaos_metrics['successful_injections'])
            with col4:
                st.metric("Success Rate", f"{chaos_metrics['injection_success_rate']}%")
            
            if st.button("🔄 Reset Chaos Metrics", use_container_width=True, key="reset_chaos_metrics"):
                result = reset_chaos_metrics()
                st.success(result['message'])
                st.rerun()
        except Exception as e:
            st.error(f"Error loading chaos metrics: {e}")
    
    # TAB 5: LOGS
    with tab5:
        st.subheader("📋 System Logs")
        
        from pathlib import Path
        import os
        
        log_dir = Path("logs")
        
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            
            if log_files:
                selected_log = st.selectbox(
                    "Select log file",
                    [log.name for log in sorted(log_files, reverse=True)],
                    key="log_file"
                )
                
                log_path = log_dir / selected_log
                
                try:
                    with open(log_path, 'r') as f:
                        log_content = f.read()
                    
                    st.text_area(
                        "Log Content",
                        value=log_content,
                        height=400,
                        disabled=True,
                        key="log_content"
                    )

                    st.download_button(
                        label="📥 Download Log",
                        data=log_content,
                        file_name=selected_log,
                        mime="text/plain",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error reading log file: {e}")
            else:
                st.info("ℹ️ No log files found yet.")
        else:
            st.warning("⚠️ Logs directory not found.")

    # TAB 6: DEBUGGING
    with tab6:
        st.subheader("🛠 Debugging & Raw Traces")

        # Show masked LangSmith key
        try:
            masked = get_masked_langsmith_key()
            st.text_input("LangSmith API Key (masked)", value=masked, disabled=True, key="ls_key_masked")
        except Exception as e:
            st.error(f"Error reading LangSmith key: {e}")

        st.markdown("---")

        # Debug logs inspector
        st.subheader("🧾 LLM Debug Logs")
        try:
            logs = get_debug_logs()
            st.write(f"Total debug entries: {len(logs)}")

            if logs:
                if st.button("📥 Download Debug Logs", key="download_debug_logs"):
                    dump = json.dumps(logs, indent=2, ensure_ascii=False)
                    st.download_button(label="Download JSON", data=dump, file_name=f"debug_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")

                with st.expander("Show latest logs (most recent first)", expanded=False):
                    for entry in reversed(logs[-50:]):
                        st.markdown(f"**{entry.get('timestamp','-')} | {entry.get('model','-')}**")
                        st.code(json.dumps(entry, indent=2, ensure_ascii=False), language='json')

                if st.button("🧽 Clear Debug Logs", key="clear_debug_logs"):
                    clear_debug_logs()
                    st.success("Debug logs cleared")
                    st.rerun()
            else:
                st.info("No debug logs yet.")
        except Exception as e:
            st.error(f"Error loading debug logs: {e}")

        st.markdown("---")

        # Run an ad-hoc debug request
        st.subheader("⚙️ Run Ad-hoc Debug Request")
        debug_input = st.text_area("Enter a debug user message", value="Debug: run a quick test blog generation", height=120, key="debug_input")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Run Debug Request", key="run_debug_request"):
                with st.spinner("Running debug request..."):
                    try:
                        resp = process_blog_request(debug_input)
                        st.subheader("Response")
                        st.write(resp)
                        # Offer to save the response to LangSmith/out file
                        if st.button("📤 Save Response to LangSmith Out File", key="save_resp_ls"):
                            detail = save_event_to_langsmith({"debug_input": debug_input, "response": resp, "timestamp": datetime.now().isoformat()})
                            st.write(detail)
                    except Exception as e:
                        st.error(f"Debug request failed: {e}")

        with col2:
            st.subheader("Last Response Preview")
            try:
                last_logs = get_debug_logs()
                if last_logs:
                    st.code(json.dumps(last_logs[-1], indent=2, ensure_ascii=False), language='json')
                else:
                    st.info("No recent logs to preview")
            except Exception as e:
                st.error(f"Error showing last response: {e}")

st.markdown("---")

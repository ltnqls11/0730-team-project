import streamlit as st
from ai_services import SmartFridgeAI
from database import SmartFridgeDB
import time

def cooking_assistant_page():
    """요리 도우미 페이지"""
    st.header("👨‍🍳 AI 요리 도우미")
    
    if 'cooking_session' not in st.session_state:
        st.session_state.cooking_session = {
            'recipe_name': '',
            'current_step': 0,
            'total_steps': 0,
            'is_cooking': False,
            'timer_start': None,
            'step_notes': []
        }
    
    ai = SmartFridgeAI()
    db = SmartFridgeDB()
    
    if not st.session_state.cooking_session['is_cooking']:
        # 요리 시작 화면
        st.markdown("""
        ### 🍳 요리를 시작해보세요!
        AI 도우미가 단계별로 요리를 도와드립니다.
        """)
        
        # 레시피 선택
        if st.session_state.user_id:
            recipes = db.get_recipes(st.session_state.user_id)
            if recipes:
                recipe_options = {f"{r['name']} ({r['category']})": r for r in recipes}
                selected_recipe_key = st.selectbox("요리할 레시피 선택", list(recipe_options.keys()))
                selected_recipe = recipe_options[selected_recipe_key]
                
                # 레시피 정보 표시
                with st.expander("📖 레시피 정보"):
                    st.write(f"**설명:** {selected_recipe['description']}")
                    st.write(f"**재료:** {selected_recipe['ingredients_list']}")
                    st.write(f"**조리시간:** {selected_recipe['cooking_time']}분")
                    st.write(f"**난이도:** {selected_recipe['difficulty']}")
                
                # 요리 시작 버튼
                if st.button("🚀 요리 시작하기", type="primary"):
                    st.session_state.cooking_session.update({
                        'recipe_name': selected_recipe['name'],
                        'current_step': 1,
                        'total_steps': len(selected_recipe['ingredients_list'].split(',')) + 3,  # 대략적인 단계 수
                        'is_cooking': True,
                        'timer_start': time.time(),
                        'step_notes': []
                    })
                    st.rerun()
            else:
                st.warning("등록된 레시피가 없습니다. 먼저 레시피를 등록해주세요.")
        
        # 직접 요리명 입력
        st.markdown("---")
        st.subheader("🔍 또는 요리명을 직접 입력하세요")
        custom_recipe = st.text_input("요리명", placeholder="김치찌개, 불고기 등")
        
        if st.button("🍳 바로 요리 시작", type="secondary"):
            if custom_recipe:
                st.session_state.cooking_session.update({
                    'recipe_name': custom_recipe,
                    'current_step': 1,
                    'total_steps': 10,  # 기본값
                    'is_cooking': True,
                    'timer_start': time.time(),
                    'step_notes': []
                })
                st.rerun()
            else:
                st.error("요리명을 입력해주세요.")
    
    else:
        # 요리 진행 화면
        recipe_name = st.session_state.cooking_session['recipe_name']
        current_step = st.session_state.cooking_session['current_step']
        total_steps = st.session_state.cooking_session['total_steps']
        
        # 진행률 표시
        progress = current_step / total_steps
        st.progress(progress)
        st.write(f"**{recipe_name}** 요리 중... ({current_step}/{total_steps} 단계)")
        
        # 경과 시간
        if st.session_state.cooking_session['timer_start']:
            elapsed_time = int(time.time() - st.session_state.cooking_session['timer_start'])
            minutes, seconds = divmod(elapsed_time, 60)
            st.metric("경과 시간", f"{minutes:02d}:{seconds:02d}")
        
        # AI 도움말 가져오기
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🤖 AI 도움말 받기", type="primary"):
                with st.spinner("AI가 조언을 준비하고 있습니다..."):
                    try:
                        advice = ai.get_cooking_assistant(recipe_name, current_step)
                        st.success("👨‍🍳 AI 조언")
                        st.info(advice)
                        
                        # 조언을 세션에 저장
                        st.session_state.cooking_session['step_notes'].append({
                            'step': current_step,
                            'advice': advice,
                            'timestamp': time.time()
                        })
                        
                    except Exception as e:
                        st.error(f"AI 도움말을 가져오는 중 오류가 발생했습니다: {str(e)}")
        
        with col2:
            # 단계 이동 버튼
            if st.button("⬅️ 이전 단계"):
                if current_step > 1:
                    st.session_state.cooking_session['current_step'] -= 1
                    st.rerun()
            
            if st.button("➡️ 다음 단계"):
                if current_step < total_steps:
                    st.session_state.cooking_session['current_step'] += 1
                    st.rerun()
        
        # 현재 단계 정보
        st.markdown(f"### 📋 {current_step}단계")
        
        # 사용자 메모
        user_note = st.text_area(
            "이 단계에서의 메모", 
            placeholder="온도, 시간, 특이사항 등을 기록하세요...",
            key=f"note_step_{current_step}"
        )
        
        if st.button("📝 메모 저장"):
            if user_note:
                st.session_state.cooking_session['step_notes'].append({
                    'step': current_step,
                    'user_note': user_note,
                    'timestamp': time.time()
                })
                st.success("메모가 저장되었습니다!")
        
        # 재료 대체 기능
        st.markdown("---")
        st.subheader("🔄 재료 대체 추천")
        missing_ingredient = st.text_input("부족한 재료", placeholder="예: 양파")
        
        if st.button("🔍 대체재 찾기"):
            if missing_ingredient:
                with st.spinner("대체 가능한 재료를 찾고 있습니다..."):
                    try:
                        substitutes = ai.suggest_ingredient_substitutes(missing_ingredient, recipe_name)
                        
                        if substitutes:
                            st.success(f"🎯 {missing_ingredient}의 대체재 추천")
                            for sub in substitutes:
                                st.write(f"• **{sub['substitute']}**: {sub['reason']}")
                        else:
                            st.warning("적절한 대체재를 찾지 못했습니다.")
                            
                    except Exception as e:
                        st.error(f"대체재 검색 중 오류가 발생했습니다: {str(e)}")
        
        # 요리 완료/중단 버튼
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ 요리 완료", type="primary"):
                st.session_state.cooking_session['is_cooking'] = False
                st.success(f"🎉 {recipe_name} 요리가 완료되었습니다!")
                
                # 요리 기록 저장 (선택사항)
                total_time = int(time.time() - st.session_state.cooking_session['timer_start'])
                st.info(f"총 소요시간: {total_time//60}분 {total_time%60}초")
                
                st.rerun()
        
        with col2:
            if st.button("⏸️ 일시정지"):
                st.info("요리가 일시정지되었습니다.")
        
        with col3:
            if st.button("❌ 요리 중단"):
                st.session_state.cooking_session['is_cooking'] = False
                st.warning("요리가 중단되었습니다.")
                st.rerun()
        
        # 이전 단계 기록 보기
        if st.session_state.cooking_session['step_notes']:
            with st.expander("📚 이전 단계 기록"):
                for note in reversed(st.session_state.cooking_session['step_notes']):
                    timestamp = time.strftime("%H:%M:%S", time.localtime(note['timestamp']))
                    st.write(f"**{note['step']}단계 ({timestamp})**")
                    
                    if 'advice' in note:
                        st.info(f"🤖 AI 조언: {note['advice']}")
                    if 'user_note' in note:
                        st.write(f"📝 메모: {note['user_note']}")
                    st.write("---")

def smart_timer():
    """스마트 타이머 기능"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏰ 스마트 타이머")
    
    # 타이머 설정
    timer_minutes = st.sidebar.number_input("분", min_value=0, max_value=60, value=0)
    timer_seconds = st.sidebar.number_input("초", min_value=0, max_value=59, value=30)
    
    total_seconds = timer_minutes * 60 + timer_seconds
    
    if 'timer_end' not in st.session_state:
        st.session_state.timer_end = None
    
    if st.sidebar.button("⏰ 타이머 시작"):
        if total_seconds > 0:
            st.session_state.timer_end = time.time() + total_seconds
            st.sidebar.success(f"타이머 시작: {timer_minutes}분 {timer_seconds}초")
    
    # 타이머 표시
    if st.session_state.timer_end:
        remaining = st.session_state.timer_end - time.time()
        
        if remaining > 0:
            mins, secs = divmod(int(remaining), 60)
            st.sidebar.metric("남은 시간", f"{mins:02d}:{secs:02d}")
            
            # 자동 새로고침을 위한 placeholder
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("⏰ 타이머 완료!")
            st.sidebar.balloons()
            st.session_state.timer_end = None

if __name__ == "__main__":
    cooking_assistant_page()
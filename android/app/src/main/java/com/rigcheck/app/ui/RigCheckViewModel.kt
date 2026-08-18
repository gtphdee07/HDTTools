package com.rigcheck.app.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rigcheck.app.data.RecentRigsRepository
import com.rigcheck.app.domain.BreakdownItem
import com.rigcheck.app.domain.VerdictInfo
import com.rigcheck.app.domain.computeBreakdown
import com.rigcheck.app.domain.model.RecentRig
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import com.rigcheck.app.domain.verdictFor
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

// Nav-graph-scoped: one instance shared across every screen so the
// in-progress truck/trailer/scale data survives navigating back and forth.
// disclaimerAcknowledged is deliberately never persisted - session/process-
// scoped only, per ANDROID_DESIGN_BRIEF.md ("shown once per app session").
class RigCheckViewModel(application: Application) : AndroidViewModel(application) {
    private val recentRigsRepository = RecentRigsRepository(application)

    val recentRigs: StateFlow<List<RecentRig>> = recentRigsRepository.recentRigs
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    var rigNickname by mutableStateOf("")
        private set
    var truck by mutableStateOf(TruckTag())
    var trailer by mutableStateOf(TrailerTag())
    var scale by mutableStateOf(ScaleTicket())
    var disclaimerAcknowledged by mutableStateOf(false)
        private set

    val breakdown: List<BreakdownItem>
        get() = computeBreakdown(truck, trailer, scale)

    val verdict: VerdictInfo
        get() = verdictFor(breakdown)

    fun selectRecentRig(rig: RecentRig) {
        rigNickname = rig.nickname
        truck = rig.truck
        trailer = rig.trailer
        scale = ScaleTicket()
    }

    fun startNewRig(nickname: String) {
        rigNickname = nickname
        truck = TruckTag()
        trailer = TrailerTag()
        scale = ScaleTicket()
    }

    fun acknowledgeDisclaimer() {
        disclaimerAcknowledged = true
    }

    fun saveCurrentRig() {
        viewModelScope.launch { recentRigsRepository.saveRecentRig(rigNickname, truck, trailer) }
    }
}

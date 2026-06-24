package com.example.messenger.models

import com.google.gson.annotations.SerializedName
import java.util.UUID

data class Chat(
    val id: UUID,
    val name: String? = null,
    @SerializedName("is_group") val isGroup: Boolean = false,
    val participants: List<User> = emptyList(),
    @SerializedName("created_at") val createdAt: String
)

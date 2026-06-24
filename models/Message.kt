package com.example.messenger.models

import com.google.gson.annotations.SerializedName
import java.util.UUID

data class Message(
    val id: UUID,
    val chat: UUID,
    val sender: User,
    val text: String = "",
    @SerializedName("media_url") val mediaUrl: String? = null,
    @SerializedName("media_type") val mediaType: String = "",
    val timestamp: String,
    @SerializedName("updated_at") val updatedAt: String,
    @SerializedName("is_deleted") val isDeleted: Boolean = false,
    val reactions: Map<String, Int> = emptyMap()
)
